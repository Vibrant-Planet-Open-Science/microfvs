"""Python client for the MicroFVS web service."""

from __future__ import annotations

import os
import time
from typing import Any

import httpx2
from pydantic import SecretStr
from pydantic_core import to_jsonable_python

from microfvs.enums import FvsVariant
from microfvs.exceptions import FvsTemplateRenderError
from microfvs.models import (
    FvsEvent,
    FvsResult,
    FvsStandInit,
    FvsStandStockParams,
    FvsTreeInit,
)

BASE_URL_ENV_VAR = "MICROFVS_BASE_URL"
CREDENTIAL_ENV_VARS = {
    "client_id": "MICROFVS_CLIENT_ID",
    "client_secret": "MICROFVS_CLIENT_SECRET",
    "api_key": "MICROFVS_API_KEY",
    "token_url": "MICROFVS_TOKEN_URL",
}
MAX_ERROR_BODY_CHARS = 500
SCOPE = "microfvs-api/read"
TOKEN_REFRESH_MARGIN = 60  # seconds before expiry to fetch a new token


class MicroFvsClient:
    """Client for calling a MicroFVS web service.

    Attributes:
        base_url (str): root URL of the service, without a trailing
            slash, e.g. `http://localhost:8080`.
        session (httpx2.Client): HTTP session used for all requests.
            Configure proxies or CA bundles on it as needed.
    """

    def __init__(
        self,
        base_url: str | None = None,
        *,
        client_id: str | None = None,
        client_secret: str | SecretStr | None = None,
        api_key: str | SecretStr | None = None,
        token_url: str | None = None,
        timeout: float = 30,
    ):
        """Creates a client.

        Pass all four credentials (or set their environment variables)
        to call the hosted service; pass none for an unauthenticated
        service such as a local container.

        Args:
            base_url (str, optional): root URL of the service. Falls
                back to the `MICROFVS_BASE_URL` environment variable.
            client_id (str, optional): Cognito app client ID. Falls back
                to `MICROFVS_CLIENT_ID`.
            client_secret (str | SecretStr, optional): Cognito app
                client secret. Falls back to `MICROFVS_CLIENT_SECRET`.
            api_key (str | SecretStr, optional): API Gateway key sent as
                `x-api-key`. Falls back to `MICROFVS_API_KEY`.
            token_url (str, optional): Cognito OAuth2 token endpoint.
                Falls back to `MICROFVS_TOKEN_URL`.
            timeout (float): seconds to wait for each request.

        Raises:
            ValueError: if no base URL is given or set in the
                environment, or if only some credentials are.
        """
        base_url = base_url or os.environ.get(BASE_URL_ENV_VAR)
        if not base_url:
            msg = f"Pass base_url or set {BASE_URL_ENV_VAR}."
            raise ValueError(msg)
        self.base_url = base_url.rstrip("/")
        self.session = httpx2.Client(timeout=timeout)

        env = os.environ.get
        self._client_id = client_id or env(CREDENTIAL_ENV_VARS["client_id"])
        self._client_secret = _secret(
            client_secret or env(CREDENTIAL_ENV_VARS["client_secret"])
        )
        self._api_key = _secret(api_key or env(CREDENTIAL_ENV_VARS["api_key"]))
        self._token_url = token_url or env(CREDENTIAL_ENV_VARS["token_url"])
        resolved = [
            self._client_id,
            self._client_secret,
            self._api_key,
            self._token_url,
        ]
        env_vars = CREDENTIAL_ENV_VARS.values()
        missing = [e for e, v in zip(env_vars, resolved) if not v]
        if 0 < len(missing) < len(resolved):
            msg = f"Incomplete credentials; pass or set {', '.join(missing)}."
            raise ValueError(msg)
        self._token: SecretStr | None = None
        self._expires_at = 0.0

    def _access_token(self) -> SecretStr:
        """Returns the cached access token, fetching one if needed."""
        if self._token is None or time.monotonic() >= self._expires_at:
            # Only reached with all credentials set (see _auth_headers).
            assert self._client_id and self._client_secret and self._token_url
            resp = self.session.post(
                self._token_url,
                auth=(self._client_id, self._client_secret.get_secret_value()),
                data={"grant_type": "client_credentials", "scope": SCOPE},
            )
            _raise_for_status(resp)
            body = resp.json()
            self._token = SecretStr(body["access_token"])
            self._expires_at = (
                time.monotonic() + body["expires_in"] - TOKEN_REFRESH_MARGIN
            )
        return self._token

    def _auth_headers(self) -> dict[str, str]:
        if self._api_key is None:
            return {}
        return {
            "Authorization": f"Bearer {self._access_token().get_secret_value()}",
            "x-api-key": self._api_key.get_secret_value(),
        }

    def _request(self, method: str, path: str, **kwargs) -> httpx2.Response:
        url = f"{self.base_url}/{path}"
        resp = self.session.request(
            method, url, headers=self._auth_headers(), **kwargs
        )
        if (
            resp.status_code == httpx2.codes.UNAUTHORIZED
            and self._api_key is not None
        ):
            self._token = None  # expired or revoked early; retry once
            resp = self.session.request(
                method, url, headers=self._auth_headers(), **kwargs
            )
        _raise_for_status(resp)
        return resp

    def healthcheck(self) -> dict[str, str]:
        """Returns the service's liveness status."""
        return self._request("GET", "healthcheck").json()

    def version(self) -> dict[str, str]:
        """Returns the versions of FVS running in the service."""
        return self._request("GET", "version").json()

    def template(self) -> dict:
        """Returns the default keyfile template and its parameters."""
        return self._request("GET", "template").json()

    def treatments(self) -> list[str]:
        """Returns all USFS treatment codes known to the service."""
        return self._request("GET", "treatments").json()["USFS Treatments"]

    def treatment(self, code: str) -> str:
        """Returns the KCP content for a USFS treatment code.

        Args:
            code (str): treatment code, e.g. `"06-03"`.
        """
        return self._request("GET", f"treatments/{code}").text

    def keyfile(
        self,
        variant: FvsVariant | str,
        stand_id: str | int,
        *,
        template: str | None = None,
        template_params: dict | None = None,
        treatments: list[str | FvsEvent] | None = None,
        disturbances: list[str | FvsEvent] | None = None,
    ) -> str:
        """Renders an FVS keyfile on the service.

        Optional arguments left as None use the service's defaults.

        Args:
            variant (FvsVariant | str): regional FVS variant code.
            stand_id (str | int): stand identifier.
            template (str, optional): Jinja2 FVS keyfile template.
            template_params (dict, optional): template variables.
            treatments (list[str | FvsEvent], optional): treatment
                codes or explicit events.
            disturbances (list[str | FvsEvent], optional): disturbance
                codes or explicit events.

        Raises:
            FvsTemplateRenderError: if the template is missing required
                variables.
        """
        body = _body(
            variant=variant,
            stand_id=stand_id,
            template=template,
            template_params=template_params,
            treatments=treatments,
            disturbances=disturbances,
        )
        return self._request("POST", "keyfile", json=body).text

    def run(
        self,
        stand_init: FvsStandInit,
        tree_init: FvsTreeInit | None = None,
        *,
        template: str | None = None,
        template_params: dict | None = None,
        treatments: list[str | FvsEvent] | None = None,
        disturbances: list[str | FvsEvent] | None = None,
        stand_stock_params: FvsStandStockParams | None = None,
    ) -> FvsResult:
        """Runs FVS on a single stand on the service.

        Optional arguments left as None use the service's defaults
        (e.g. no `tree_init` simulates bare ground).

        Args:
            stand_init (FvsStandInit): stand initialization data.
            tree_init (FvsTreeInit, optional): tree initialization data.
            template (str, optional): Jinja2 FVS keyfile template.
            template_params (dict, optional): template variables.
            treatments (list[str | FvsEvent], optional): treatment
                codes or explicit events.
            disturbances (list[str | FvsEvent], optional): disturbance
                codes or explicit events.
            stand_stock_params (FvsStandStockParams, optional): controls
                Stand-and-Stock table generation.

        Raises:
            FvsTemplateRenderError: if the template is missing required
                variables.
        """
        body = _body(
            stand_init=stand_init,
            tree_init=tree_init,
            template=template,
            template_params=template_params,
            treatments=treatments,
            disturbances=disturbances,
            stand_stock_params=stand_stock_params,
        )
        resp = self._request("POST", "run", json=body)
        return FvsResult.model_validate(resp.json())


def _secret(value: str | SecretStr | None) -> SecretStr | None:
    """Wraps a plain string so it is masked in reprs and tracebacks."""
    if value is None or isinstance(value, SecretStr):
        return value
    return SecretStr(value)


def _body(**fields: Any) -> dict:
    """Builds a JSON request body, omitting fields that are None.

    Omitted fields fall back to the service's defaults; sending null
    instead would fail validation for fields like `tree_init`.
    """
    return to_jsonable_python(
        {key: val for key, val in fields.items() if val is not None}
    )


def _raise_for_status(resp: httpx2.Response) -> None:
    """Raises an informative error for 4xx/5xx responses."""
    if not resp.is_error:
        return
    try:
        body = resp.json()
    except ValueError:
        body = None
    if (
        resp.status_code == httpx2.codes.UNPROCESSABLE_CONTENT
        and isinstance(body, dict)
        and "missing_required" in body
    ):
        raise FvsTemplateRenderError(
            template_variables=body["template_variables"],
            provided_variables=body["provided_variables"],
            missing_required=body["missing_required"],
            missing_optional=body["missing_optional"],
        )
    msg = f"{resp.status_code} error for {resp.request.method} {resp.url}"
    if resp.status_code == httpx2.codes.FORBIDDEN:
        msg += (
            ". Check the x-api-key header and that the URL includes the "
            "service's path prefix (e.g. /microfvs)"
        )
    if resp.text:
        msg += f": {resp.text[:MAX_ERROR_BODY_CHARS]}"
    raise httpx2.HTTPStatusError(msg, request=resp.request, response=resp)
