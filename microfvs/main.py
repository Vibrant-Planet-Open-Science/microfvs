from __future__ import annotations

import importlib.resources
from typing import Annotated

from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse

from microfvs.constants import (
    EXAMPLE_DISTURBANCE_EVENT,
    EXAMPLE_TREATMENT_STR,
    TEST_STANDINIT_RECORDS,
    TEST_TREEINIT_RECORDS,
)
from microfvs.enums import FvsKeyfileTemplate
from microfvs.exceptions import FvsTemplateRenderError
from microfvs.models import (
    FvsEventLibrary,
    FvsEventType,
    FvsKeyfileRequest,
    FvsResult,
    FvsRunRequest,
    FvsStandInit,
    FvsTreeInit,
    FvsVariant,
)
from microfvs.utils.fvs_version import get_fvs_versions
from microfvs.utils.run_fvs import run_fvs_keyfile
from microfvs.utils.template_helpers import (
    ClassifiedTemplateVariables,
    classify_fvs_keyfile_template_variables,
)

app = FastAPI()


@app.get("/healthcheck", status_code=200)
async def health_check() -> dict[str, str]:
    """Health check for the load balancer target group. Returns 200."""
    return {"status": "ok"}


@app.exception_handler(FvsTemplateRenderError)
async def template_render_error_handler(
    request: Request,  # noqa: ARG001
    exc: FvsTemplateRenderError,
) -> JSONResponse:
    """Return a 422 with details about missing template variables."""
    return JSONResponse(
        status_code=422,
        content={
            "detail": str(exc),
            "template_variables": exc.template_variables,
            "provided_variables": exc.provided_variables,
            "missing_required": exc.missing_required,
            "missing_optional": exc.missing_optional,
        },
    )


KEYFILE_REQUEST_EXAMPLE = {
    "variant": FvsVariant.PN.value,
    "stand_id": "12345",
    "template_params": {"num_cycles": 1, "cycle_length": 5},
    "treatments": [EXAMPLE_TREATMENT_STR],
    "disturbances": [EXAMPLE_DISTURBANCE_EVENT],
}
RUN_REQUEST_EXAMPLE = {
    "stand_init": FvsStandInit.model_validate(TEST_STANDINIT_RECORDS[0]),
    "tree_init": FvsTreeInit.from_records(TEST_TREEINIT_RECORDS),
    "template_params": {"num_cycles": 10, "cycle_length": 5},
    "treatments": [EXAMPLE_TREATMENT_STR],
    "disturbances": [EXAMPLE_DISTURBANCE_EVENT],
}


@app.get("/", response_class=HTMLResponse)
def read_html(request: Request) -> str:
    """Returns a simple HTML page confirming MicroFVS is running."""
    docs_url = request.scope.get("root_path", "") + "/docs"
    return f"""
    <html>
        <body>
            <h1>MicroFVS is running!</h1>
            <p>This is a simple web service for running FVS simulations.</p>
            <p>To get started, go to the <a href="{docs_url}">API documentation</a>.</p>
        </body>
    </html>
    """


@app.get("/version")
def check_fvs_version() -> dict[str, str]:
    """Reports the version of FVS running in the web service."""
    return get_fvs_versions()


@app.get("/template")
def example_keyfile_template() -> dict[str, str | ClassifiedTemplateVariables]:
    """Return default template for simulating a single stand in FVS."""
    template = FvsKeyfileTemplate.DEFAULT
    template_params = classify_fvs_keyfile_template_variables(template)
    return {
        "template_params": template_params,
        "template": template,
    }


@app.post("/keyfile", response_class=PlainTextResponse)
def generate_keyfile_from_template(
    body: Annotated[
        FvsKeyfileRequest, Body(examples=[KEYFILE_REQUEST_EXAMPLE])
    ],
) -> str:
    """Generates a FVS Keyfile with user-specified parameters.

    Treatments and disturbances accept string keys resolved via the
    event library, or explicit FvsEvent objects.
    """
    return body.keyfile.content


@app.post("/run")
def run_fvs_single_stand(
    body: Annotated[FvsRunRequest, Body(examples=[RUN_REQUEST_EXAMPLE])],
) -> FvsResult:
    """Runs FVS on a single stand and returns the results.

    If ``tree_init`` is omitted, bare ground is simulated. ``variant``
    and ``stand_id`` are derived from ``stand_init``. Treatments and
    disturbances accept string keys resolved via the event library, or
    explicit FvsEvent objects.
    """
    return run_fvs_keyfile(
        stand_init=body.stand_init,
        tree_init=body.tree_init,
        keyfile=body.keyfile,
        stand_stock_params=body.stand_stock_params,
    )


@app.get("/treatments")
def all_usfs_fvs_treatment_codes() -> dict[str, list[str]]:
    """Returns all USFS FVS treament codes."""
    with importlib.resources.as_file(
        importlib.resources.files("microfvs.keyword_components.treatments.usfs")
    ) as path:
        return {
            "USFS Treatments": sorted([x.stem for x in path.rglob("*.kcp")])
        }


@app.get("/treatments/{treatment_code}", response_class=PlainTextResponse)
def get_treatment_kcp(treatment_code: str) -> str:
    """Gets the content of a FVS FvsEvent KCP file.

    Args:
        treatment_code (str): code for treatment recognized by MicroFVS
    """
    library = FvsEventLibrary()
    if treatment_code not in library.treatments:
        raise HTTPException(status_code=404, detail="Treatment not found.")
    treatment = library.lookup(
        event_type=FvsEventType.TREATMENT, event_key=treatment_code
    )
    return treatment.content
