from __future__ import annotations

import importlib.resources
from typing import Annotated

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse

from microfvs.constants import TEST_STANDINIT_RECORDS, TEST_TREEINIT_RECORDS
from microfvs.enums import FvsKeyfileTemplate
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

app = FastAPI()


@app.get("/", response_class=HTMLResponse)
def read_html() -> str:
    """Returns a simple HTML page confirming MicroFVS is running."""
    return """
    <html>
        <body>
            <h1>MicroFVS is running!</h1>
            <p>This is a simple web service for running FVS simulations.</p>
            <p>To get started, go to the <a href="/docs">API documentation</a>.</p>
        </body>
    </html>
    """


@app.get("/version")
def check_fvs_version() -> dict[str, str]:
    """Reports the version of FVS running in the web service."""
    return get_fvs_versions()


@app.get("/template", response_class=PlainTextResponse)
def example_keyfile_template() -> str:
    """Return default template for simulating a single stand in FVS."""
    return FvsKeyfileTemplate.DEFAULT


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
) -> str:
    """Generates a FVS Keyfile with user-specified parameters.

    Args:
        variant (str): Regional FVS variant code.
        stand_id (str): Stand identifier.
        template (str): Jinja2 FVS keyfile template.
        template_params (dict): Template variables to inject.
    """
    return FvsKeyfile(
        variant=variant,
        stand_id=stand_id,
        template=template,
        template_params=template_params,
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
    stand_stock_params: FvsStandStockParams = FvsStandStockParams(),
) -> FvsResult:
    """Runs FVS on a single stand and returns the results.

    Args:
        stand_init (FvsStandInit): Stand initialization data.
        tree_init (FvsTreeInit, optional): Tree initialization data.
            If not provided, bare ground will be simulated.
        template (str, optional): FVS keyfile template to use.
        template_params (dict, optional): Template variables
            (e.g. treatments, disturbances, num_cycles,
            cycle_length, and custom placeholders). ``variant``
            and ``stand_id`` are derived from ``stand_init``.
        stand_stock_params (FvsStandStockParams): Controls
            Stand-and-Stock table generation in FVS outputs.
    """
    return run_fvs(
        stand_init=stand_init,
        tree_init=tree_init,
        template=template,
        template_params=template_params,
        stand_stock_params=stand_stock_params,
    )


@app.post("/outfile", response_class=PlainTextResponse)
def get_outfile(
    stand_init: Annotated[
        FvsStandInit,
        Body(examples=[FvsStandInit.model_validate(TEST_STANDINIT_RECORDS[0])]),
    ],
    tree_init: Annotated[
        FvsTreeInit,
        Body(examples=[FvsTreeInit.from_records(TEST_TREEINIT_RECORDS)]),
    ] = FvsTreeInit(),
    treatments: Annotated[list[FvsEvent] | None, Body()] = None,
    disturbances: Annotated[list[FvsEvent] | None, Body()] = None,
    template: Annotated[
        str, Body(examples=[FvsKeyfileTemplate.DEFAULT])
    ] = FvsKeyfileTemplate.DEFAULT,
    template_params: Annotated[
        dict, Body(examples=[{"num_cycles": 10, "cycle_length": 5}])
    ] = {},
    stand_stock_params: FvsStandStockParams = FvsStandStockParams(),
) -> str:
    """Runs FVS and returns the OUT file.

    If multiple stands are included in `stand_init`, only the outfile
    from the first stand is returned.

    Args:
        stand_init (FvsStandInit): Stand initialization data for one or
            more stands. All stands represented in stand_init will be
            run in the order specified unless or until `limit` is
            reached.
        tree_init (FvsTreeInit, optional): Tree initialization data for
            one or more stands. If not provided, bare ground will be
            simulated.
        template (str, optional): FVS keyfile template to use. Defaults
            to FvsKeyfileTemplate.DEFAULT
        template_params (dict, optional): Parameters to inject into
            the keyfile template. See ``/run`` for details.
        stand_stock_params (FvsStandStockParams): Optional set of
            parameters to govern the generation of a Stand and Stock
            Table in the FVS outputs.
    """
    result = run_fvs(
        stand_init=stand_init,
        tree_init=tree_init,
        template=template,
        template_params=template_params,
        stand_stock_params=stand_stock_params,
    )
    return (
        result.outfile if isinstance(result, FvsResult) else result[0].outfile
    )


@app.get("/treatments")
def all_usfs_fvs_treatment_codes() -> dict[str, list[str]]:
    """Returns all USFS FVS treament codes."""
    with importlib.resources.as_file(
        importlib.resources.files(
            "microfvs.keyword_components.treatments.usfs"
        ).joinpath("")
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
