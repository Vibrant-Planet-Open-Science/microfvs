from __future__ import annotations

import importlib.resources
from typing import Annotated

from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse

from microfvs.constants import (
    EXAMPLE_DISTURBANCE_EVENT,
    EXAMPLE_DISTURBANCE_STR,
    EXAMPLE_TREATMENT_EVENT,
    EXAMPLE_TREATMENT_STR,
    TEST_STANDINIT_RECORDS,
    TEST_TREEINIT_RECORDS,
)
from microfvs.enums import FvsKeyfileTemplate
from microfvs.exceptions import FvsTemplateRenderError
from microfvs.models import (
    FvsEvent,
    FvsEventLibrary,
    FvsEventType,
    FvsKeyfile,
    FvsResult,
    FvsStandInit,
    FvsStandStockParams,
    FvsTreeInit,
    FvsVariant,
)
from microfvs.utils.fvs_version import get_fvs_versions
from microfvs.utils.run_fvs import run_fvs
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
    variant: Annotated[
        str,
        Body(examples=[FvsVariant.PN.value]),
    ],
    stand_id: Annotated[
        str,
        Body(examples=["12345"]),
    ],
    template: Annotated[
        str,
        Body(examples=[FvsKeyfileTemplate.DEFAULT]),
    ] = FvsKeyfileTemplate.DEFAULT,
    template_params: Annotated[
        dict, Body(examples=[{"num_cycles": 1, "cycle_length": 5}])
    ] = {},
    treatments: Annotated[
        list[str | FvsEvent] | None,
        Body(
            examples=[
                [EXAMPLE_TREATMENT_STR],
                [FvsEvent.model_validate(EXAMPLE_TREATMENT_EVENT)],
            ]
        ),
    ] = None,
    disturbances: Annotated[
        list[str | FvsEvent] | None,
        Body(
            examples=[
                [EXAMPLE_DISTURBANCE_STR],
                [FvsEvent.model_validate(EXAMPLE_DISTURBANCE_EVENT)],
            ]
        ),
    ] = None,
) -> str:
    """Generates a FVS Keyfile with user-specified parameters.

    Args:
        variant (str): Regional FVS variant code.
        stand_id (str): Stand identifier.
        template (str): Jinja2 FVS keyfile template.
        template_params (dict): Template variables to inject
            (e.g. num_cycles, cycle_length, custom placeholders).
        treatments (list[str | FvsEvent], optional): Treatment
            events to inject. Accepts string keys resolved via the
            event library, or explicit FvsEvent objects.
        disturbances (list[str | FvsEvent], optional): Disturbance
            events to inject. Same coercion rules as treatments.
    """
    return FvsKeyfile(
        variant=variant,
        stand_id=stand_id,
        template=template,
        template_params=template_params,
        treatments=treatments,
        disturbances=disturbances,
    ).content


@app.post("/run")
def run_fvs_single_stand(
    stand_init: Annotated[
        FvsStandInit,
        Body(examples=[FvsStandInit.model_validate(TEST_STANDINIT_RECORDS[0])]),
    ],
    tree_init: Annotated[
        FvsTreeInit,
        Body(examples=[FvsTreeInit.from_records(TEST_TREEINIT_RECORDS)]),
    ] = FvsTreeInit(),
    template: Annotated[
        str, Body(examples=[FvsKeyfileTemplate.DEFAULT])
    ] = FvsKeyfileTemplate.DEFAULT,
    template_params: Annotated[
        dict, Body(examples=[{"num_cycles": 10, "cycle_length": 5}])
    ] = {},
    treatments: Annotated[
        list[str | FvsEvent] | None,
        Body(
            examples=[
                [EXAMPLE_TREATMENT_STR],
                FvsEvent.model_validate(EXAMPLE_TREATMENT_EVENT),
            ]
        ),
    ] = None,
    disturbances: Annotated[
        list[str | FvsEvent] | None,
        Body(
            examples=[
                [EXAMPLE_DISTURBANCE_STR],
                [FvsEvent.model_validate(EXAMPLE_DISTURBANCE_EVENT)],
            ]
        ),
    ] = None,
    stand_stock_params: FvsStandStockParams = FvsStandStockParams(),
) -> FvsResult:
    """Runs FVS on a single stand and returns the results.

    Args:
        stand_init (FvsStandInit): Stand initialization data.
        tree_init (FvsTreeInit, optional): Tree initialization data.
            If not provided, bare ground will be simulated.
        template (str, optional): FVS keyfile template to use.
        template_params (dict, optional): Template variables
            (e.g. num_cycles, cycle_length, custom placeholders).
            ``variant`` and ``stand_id`` are derived from
            ``stand_init``.
        treatments (list[str | FvsEvent], optional): Treatment
            events to inject into the keyfile. Accepts string keys
            resolved via the event library, or explicit FvsEvent
            objects.
        disturbances (list[str | FvsEvent], optional): Disturbance
            events to inject into the keyfile. Same coercion rules
            as treatments.
        stand_stock_params (FvsStandStockParams): Controls
            Stand-and-Stock table generation in FVS outputs.
    """
    return run_fvs(
        stand_init=stand_init,
        tree_init=tree_init,
        template=template,
        template_params=template_params,
        treatments=treatments,
        disturbances=disturbances,
        stand_stock_params=stand_stock_params,
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
