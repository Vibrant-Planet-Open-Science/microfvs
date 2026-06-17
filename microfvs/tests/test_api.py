from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from microfvs.constants import TEST_STANDINIT_RECORDS, TEST_TREEINIT_RECORDS
from microfvs.main import app
from microfvs.models import FvsStandInit, FvsTreeInit


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_healthcheck(client):
    response = client.get("/healthcheck")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "MicroFVS" in response.text


def test_gzip_compression(client):
    tiny_response = client.get("/healthcheck")
    assert tiny_response.status_code == 200
    assert tiny_response.headers.get("content-encoding") is None

    large_response = client.get("/template")
    assert large_response.status_code == 200
    assert large_response.headers.get("content-encoding") == "gzip"


# ----------------------------------------------------------------------
# /version
# ----------------------------------------------------------------------
@pytest.mark.fvs
def test_version(client):
    response = client.get("/version")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert len(data) > 0


# ----------------------------------------------------------------------
# /template
# ----------------------------------------------------------------------
def test_template(client):
    response = client.get("/template")
    assert response.status_code == 200
    data = response.json()
    assert "template" in data
    assert "template_params" in data
    assert isinstance(response.json()["template"], str)
    assert len(response.json()["template"]) > 0


# ----------------------------------------------------------------------
# /treatments
# ----------------------------------------------------------------------
def test_treatments(client):
    response = client.get("/treatments")
    assert response.status_code == 200
    data = response.json()
    assert "USFS Treatments" in data
    assert len(data["USFS Treatments"]) > 0


def test_treatment_lookup_valid_code(client):
    treatments = client.get("/treatments").json()["USFS Treatments"]
    code = treatments[0]
    response = client.get(f"/treatments/{code}")
    assert response.status_code == 200
    assert len(response.text) > 0


def test_treatment_lookup_invalid_code_returns_404(client):
    response = client.get("/treatments/NOT_A_REAL_CODE")
    assert response.status_code == 404


# ----------------------------------------------------------------------
# /keyfile
# ----------------------------------------------------------------------
@pytest.fixture(scope="module")
def minimal_keyfile_payload():
    stand = FvsStandInit.model_validate(TEST_STANDINIT_RECORDS[0])
    return {
        "variant": stand.variant,
        "stand_id": stand.stand_id,
    }


def test_keyfile_renders(client, minimal_keyfile_payload):
    response = client.post("/keyfile", json=minimal_keyfile_payload)
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert len(response.text) > 0
    assert minimal_keyfile_payload["stand_id"] in response.text


def test_keyfile_missing_required_template_var(client, minimal_keyfile_payload):
    payload = {
        **minimal_keyfile_payload,
        "template_params": {"__force_missing__": True},
    }
    # Pass a template that references a variable we deliberately omit.
    payload["template"] = "{{ stand_id }} {{ required_but_missing }}"
    response = client.post("/keyfile", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert "missing_required" in data


# ----------------------------------------------------------------------
# /run
# ----------------------------------------------------------------------
@pytest.fixture(scope="module")
def run_payload():
    stand_init = FvsStandInit.model_validate(TEST_STANDINIT_RECORDS[0])
    tree_init = FvsTreeInit.from_records(TEST_TREEINIT_RECORDS)
    return {
        "stand_init": stand_init.model_dump(),
        "tree_init": tree_init.model_dump(),
        "template_params": {"num_cycles": 2, "cycle_length": 5},
    }


@pytest.mark.fvs
def test_run(client, run_payload):
    response = client.post("/run", json=run_payload)
    assert response.status_code == 200
    data = response.json()
    assert "outfile" in data
    assert len(data["outfile"]) > 0
