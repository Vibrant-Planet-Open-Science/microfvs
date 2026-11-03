from __future__ import annotations

import httpx2
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from microfvs.client import MicroFvsClient
from microfvs.constants import TEST_STANDINIT_RECORDS, TEST_TREEINIT_RECORDS
from microfvs.exceptions import FvsTemplateRenderError
from microfvs.main import app
from microfvs.models import FvsEvent, FvsResult, FvsStandInit, FvsTreeInit

STAND_INIT = FvsStandInit.model_validate(TEST_STANDINIT_RECORDS[0])
TREE_INIT = FvsTreeInit.from_records(TEST_TREEINIT_RECORDS)
SHORT_RUN = {"num_cycles": 2, "cycle_length": 5}


@pytest.fixture(scope="module")
def client():
    c = MicroFvsClient("http://testserver")
    with TestClient(app) as tc:
        c.session = tc
        yield c


def mock_client(handler, base_url="http://testserver"):
    c = MicroFvsClient(base_url)
    c.session = httpx2.Client(transport=httpx2.MockTransport(handler))
    return c


# ----------------------------------------------------------------------
# construction
# ----------------------------------------------------------------------
def test_base_url_from_env(monkeypatch):
    monkeypatch.setenv("MICROFVS_BASE_URL", "http://example.test/microfvs/")
    assert MicroFvsClient().base_url == "http://example.test/microfvs"


def test_missing_base_url_raises(monkeypatch):
    monkeypatch.delenv("MICROFVS_BASE_URL", raising=False)
    with pytest.raises(ValueError, match="MICROFVS_BASE_URL"):
        MicroFvsClient()


# ----------------------------------------------------------------------
# read-only endpoints
# ----------------------------------------------------------------------
def test_healthcheck(client):
    assert client.healthcheck() == {"status": "ok"}


@pytest.mark.fvs
def test_version(client):
    assert len(client.version()) > 0


def test_template(client):
    data = client.template()
    assert isinstance(data["template"], str)
    assert "template_params" in data


def test_treatments(client):
    assert "06-03" in client.treatments()


def test_treatment(client):
    assert len(client.treatment("06-03")) > 0


def test_treatment_not_found(client):
    with pytest.raises(httpx2.HTTPStatusError) as err:
        client.treatment("NOT_A_REAL_CODE")
    assert err.value.response.status_code == 404


def test_403_hints_at_api_key():
    c = mock_client(lambda _request: httpx2.Response(403))
    with pytest.raises(httpx2.HTTPStatusError, match="x-api-key"):
        c.healthcheck()


# ----------------------------------------------------------------------
# keyfile
# ----------------------------------------------------------------------
def test_keyfile(client):
    content = client.keyfile("PN", 12345, template_params=SHORT_RUN)
    assert "12345" in content


def test_keyfile_with_events(client):
    custom = FvsEvent(
        name="custom-thin", content="THINSDI         2030       200"
    )
    content = client.keyfile(
        STAND_INIT.variant,
        STAND_INIT.stand_id,
        template_params=SHORT_RUN,
        treatments=["06-03", custom],
    )
    assert client.treatment("06-03").strip().splitlines()[0] in content
    assert custom.content in content


def test_keyfile_missing_template_variable(client):
    with pytest.raises(FvsTemplateRenderError) as err:
        client.keyfile(
            "PN", "12345", template="{{ stand_id }} {{ required_but_missing }}"
        )
    assert "required_but_missing" in err.value.missing_required


def test_keyfile_invalid_body_includes_detail(client):
    with pytest.raises(httpx2.HTTPStatusError, match="variant") as err:
        client.keyfile("XX", "12345")
    assert err.value.response.status_code == 422


# ----------------------------------------------------------------------
# run
# ----------------------------------------------------------------------
@pytest.mark.fvs
def test_run(client):
    result = client.run(STAND_INIT, TREE_INIT, template_params=SHORT_RUN)
    assert isinstance(result, FvsResult)
    assert result.return_code == 0
    assert all(isinstance(df, pd.DataFrame) for df in result.fvs_data.values())


@pytest.mark.fvs
def test_run_omitted_tree_init_uses_server_default(client):
    # FVS itself warns (non-zero return code) on bare ground; the point
    # is that omitting tree_init is accepted rather than sent as null.
    with pytest.warns(UserWarning, match="bare ground"):
        result = client.run(STAND_INIT, template_params=SHORT_RUN)
    assert isinstance(result, FvsResult)
