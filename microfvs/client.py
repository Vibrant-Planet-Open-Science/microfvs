"""Python client for the MicroFVS web service."""

from __future__ import annotations

import base64
import os
import threading
import time
from collections.abc import Generator, Mapping
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
DEFAULT_SCOPE = "microfvs-api/read"
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
        scope: str = DEFAULT_SCOPE,
        auth: bool = True,
        timeout: float = 30,
    ):
        """Creates a client.

        Pass all four credentials (or set their environment variables)
        to call the hosted service; pass none, or `auth=False`, for an
        unauthenticated service such as a local container.

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
            scope (str): OAuth2 scope requested with each token.
            auth (bool): if False, send no credentials, ignoring any
                passed in or set in the environment.
            timeout (float): seconds to wait for each request.

        Raises:
            ValueError: if no base URL is given or set in the
                environment, if only some credentials are, or if
                credentials would be sent over plain http.
        """
        base_url = base_url or os.environ.get(BASE_URL_ENV_VAR)
        if not base_url:
            msg = f"Pass base_url or set {BASE_URL_ENV_VAR}."
            raise ValueError(msg)
        self.base_url = base_url.rstrip("/")
        self.session = httpx2.Client(timeout=timeout)

        if not auth:
            client_id = client_secret = api_key = token_url = None
        env: Mapping[str, str] = os.environ if auth else {}
        client_id = client_id or env.get(CREDENTIAL_ENV_VARS["client_id"])
        secret = _secret(
            client_secret or env.get(CREDENTIAL_ENV_VARS["client_secret"])
        )
        key = _secret(api_key or env.get(CREDENTIAL_ENV_VARS["api_key"]))
        token_url = token_url or env.get(CREDENTIAL_ENV_VARS["token_url"])
        resolved = [client_id, secret, key, token_url]
        env_vars = CREDENTIAL_ENV_VARS.values()
        missing = [e for e, v in zip(env_vars, resolved) if not v]
        if 0 < len(missing) < len(resolved):
            msg = f"Incomplete credentials; pass or set {', '.join(missing)}."
            raise ValueError(msg)
        self._auth: _CognitoAuth | None = None
        if client_id and secret and key and token_url:
            insecure = [
                u
                for u in (self.base_url, token_url)
                if not u.startswith("https://")
            ]
            if insecure:
                msg = (
                    f"Credentials are only sent over https, not to "
                    f"{', '.join(insecure)}; use https URLs, or pass "
                    "auth=False for a local service."
                )
                raise ValueError(msg)
            self._auth = _CognitoAuth(client_id, secret, key, token_url, scope)

    def _request(self, method: str, path: str, **kwargs) -> httpx2.Response:
        url = f"{self.base_url}/{path}"
        # Redirected requests keep x-api-key even across origins, so a
        # session configured with follow_redirects must not apply here.
        resp = self.session.request(
            method, url, auth=self._auth, follow_redirects=False, **kwargs
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


class _CognitoAuth(httpx2.Auth):
    """Sends a cached Cognito access token and the API Gateway key.

    Fetches a token when there is none or it is near expiry, and once
    more if the service rejects a cached token with 401. The lock
    makes threads sharing a client wait for one token fetch.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: SecretStr,
        api_key: SecretStr,
        token_url: str,
        scope: str,
    ):
        pair = f"{client_id}:{client_secret.get_secret_value()}"
        self._basic = SecretStr(
            "Basic " + base64.b64encode(pair.encode()).decode()
        )
        self._api_key = api_key
        self._token_url = token_url
        self._scope = scope
        self._lock = threading.Lock()
        self._token: SecretStr | None = None
        self._expires_at = 0.0

    def sync_auth_flow(
        self, request: httpx2.Request
    ) -> Generator[httpx2.Request, httpx2.Response, None]:
        if request.url.scheme != "https":  # e.g. base_url changed later
            msg = f"Credentials are only sent over https, not to {request.url}"
            raise ValueError(msg)
        token, fetched = yield from self._token_flow()
        try:
            self._apply(request, token)
            response = yield request
            # A token fetched just now failing again means bad config.
            if (
                response.status_code == httpx2.codes.UNAUTHORIZED
                and not fetched
            ):
                token, _ = yield from self._token_flow(stale=token)
                self._apply(request, token)
                yield request
        finally:
            # Runs once sent, on success, error or exception. httpx only
            # masks Authorization; keep the key out of errors and logs.
            request.headers["x-api-key"] = "[secure]"

    def _token_flow(
        self, stale: SecretStr | None = None
    ) -> Generator[httpx2.Request, httpx2.Response, tuple[SecretStr, bool]]:
        """Returns the current token and whether it was just fetched.

        Fetches a new one if there is none, it is near expiry, or it
        is still `stale` (i.e. not already replaced by another thread).
        """
        with self._lock:
            if (
                self._token is not None
                and self._token is not stale
                and time.monotonic() < self._expires_at
            ):
                return self._token, False
            resp = yield httpx2.Request(
                "POST",
                self._token_url,
                headers={"Authorization": self._basic.get_secret_value()},
                data={"grant_type": "client_credentials", "scope": self._scope},
            )
            resp.read()  # overriding sync_auth_flow skips the auto-read
            if resp.is_error:
                msg = (
                    f"{resp.status_code} error fetching a token from "
                    f"{self._token_url}: {resp.text[:MAX_ERROR_BODY_CHARS]}"
                )
                raise httpx2.HTTPStatusError(
                    msg, request=resp.request, response=resp
                )
            body = resp.json()
            self._token = SecretStr(body["access_token"])
            ttl = body.get("expires_in", 3600)
            self._expires_at = time.monotonic() + max(
                ttl - TOKEN_REFRESH_MARGIN, ttl / 2
            )
            return self._token, True

    def _apply(self, request: httpx2.Request, token: SecretStr) -> None:
        request.headers["Authorization"] = f"Bearer {token.get_secret_value()}"
        request.headers["x-api-key"] = self._api_key.get_secret_value()


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
