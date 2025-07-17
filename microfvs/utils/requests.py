from http import HTTPMethod

import requests

from microfvs.constants import CONTENT_TYPE
from microfvs.enums import FvsKeyfileTemplate, FvsVariant, ResponseContentType
from microfvs.models import FvsEvent, FvsKeyfileTemplateParams


class RequestWrapper:
    """A basic wrapper for REST API requests."""

    def __init__(self, hostname: str, api_key: str | None = None):
        self.url = f"http://{hostname}"
        self._api_key = api_key

    def _request(
        self,
        method: HTTPMethod,
        endpoint: str,
        params: dict | None = None,
        data: dict | None = None,
    ) -> str | dict:
        """Generic web request method.

        This class is currently limited to parsing web requests that return JSON
        or plain text.

        Args:
            method (HTTPMethod): the type of web request to make.
            endpoint (str): path to API endpoint, include the leading '/'.
            params (dict | None): optional dictionary of parameters to be
                included in the URL of the request.
            data (dict | None): optional dictionary of items to be included in
                body of the request.

        Returns:
            str or dict (JSON) depending on the content type of response.
        """
        full_url = f"{self.url}{endpoint}"
        headers = {"x-api-key": self._api_key}
        response = requests.request(
            method=method,
            url=full_url,
            headers=headers,
            params=params,
            json=data,
        )
        content_type = response.headers.get(CONTENT_TYPE)

        if response.status_code >= 200 and response.status_code <= 299:
            if content_type == ResponseContentType.TEXT_PLAIN:
                return response.text
            return response.json()
        raise Exception(response.json()["message"])

    def get(self, endpoint: str, params: dict | None = None) -> str | dict:
        """Executes a GET request.

        Args:
            endpoint (str): path to API endpoint, include the leading '/'.
            params (dict): dictionary of parameters to be included in the URL of
                the GET request.

        Returns:
            str or dict (JSON) depending on the content type of response.
        """
        return self._request(
            method=HTTPMethod.GET, endpoint=endpoint, params=params
        )

    def post(
        self,
        endpoint: str,
        params: dict | None = None,
        data: dict | None = None,
    ) -> str | dict:
        """Executes a POST request.

        Args:
            endpoint (str): path to API endpoint, include the leading '/'.
            params (dict | None): optional dictionary of parameters to be
                included in the URL of the POST request.
            data (dict | None): optional dictionary of items to be included in
                body of the POST request.

        Returns:
            str or dict (JSON) depending on the content type of response.
        """
        return self._request(
            method=HTTPMethod.POST,
            endpoint=endpoint,
            params=params,
            data=data,
        )


class MicroFvsRequestWrapper(RequestWrapper):
    """A wrapper for making requests using the MicroFVS Web API."""

    def template(self) -> str:
        """Gets an example FVS Keyfile template."""
        return str(self.get("/template"))

    def keyfile(
        self,
        variant: FvsVariant,
        stand_id: str,
        num_cycles: int = 1,
        cycle_length: int = 5,
        treatments: list[FvsEvent] = [
            FvsEvent(name="NONE", content="*** NO TREATMENT ***")
        ],
        disturbances: list[FvsEvent] = [
            FvsEvent(name="NONE", content="*** NO DISTURBANCE ***")
        ],
        template: str = FvsKeyfileTemplate.DEFAULT,
        **kwargs,
    ) -> str:
        """Generates a FVS Keyfile from a template.

        Args:
            variant (FvsVariant): FVS regional variant to be used
            stand_id (str): Stand identifier
            num_cycles (int, optional): number of cycles for FVS to simulate,
                defaults to 1.
            cycle_length (int, optional): length of each cycle in years,
                defaults to 5-year cycles.
            treatments (list[FvsEvent], optional): list of treatments to be
                injected into the keyfile template. Defaults to inserting
                a single event that is grow only (no management).
            disturbances (list[FvsEvent], optional): list of disturbances to be
                injected into the keyfile template. Defaults to inserting
                a single event that is undisturbed (no disturbance).
            template (str): str containing jinja2 FVS Keyfile template
            **kwargs: additional parameters to be injected into the keyfile
                template. To work, the keyfile template should have a
                placeholder corresponding to the kwarg name, and the keyfile
                will be replaced with the kwarg value.
        """
        params = FvsKeyfileTemplateParams(
            variant=variant,
            stand_id=stand_id,
            num_cycles=num_cycles,
            cycle_length=cycle_length,
            treatments=treatments,
            disturbances=disturbances,
            **kwargs,
        )
        return str(
            self.post("/keyfile", data={"template": template, "params": params})
        )
