from __future__ import annotations

import httpx2
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from microfvs.client import CREDENTIAL_ENV_VARS, MicroFvsClient
from microfvs.constants import TEST_STANDINIT_RECORDS, TEST_TREEINIT_RECORDS
from microfvs.exceptions import FvsTemplateRenderError
from microfvs.main import app
from microfvs.models import FvsEvent, FvsResult, FvsStandInit, FvsTreeInit

STAND_INIT = FvsStandInit.model_validate(TEST_STANDINIT_RECORDS[0])
TREE_INIT = FvsTreeInit.from_records(TEST_TREEINIT_RECORDS)
SHORT_RUN = {"num_cycles": 2, "cycle_length": 5}
CREDS = {
    "client_id": "test-client-id",
    "client_secret": "test-client-secret",
    "api_key": "test-api-key",
    "token_url": "http://auth.test/oauth2/token",
}


@pytest.fixture(autouse=True)
def no_credential_env(monkeypatch):
    """Keeps a developer's real credentials out of the tests."""
    for env_var in CREDENTIAL_ENV_VARS.values():
        monkeypatch.delenv(env_var, raising=False)


@pytest.fixture(scope="module")
def client():
    with pytest.MonkeyPatch.context() as mp:
        for env_var in CREDENTIAL_ENV_VARS.values():
            mp.delenv(env_var, raising=False)
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


# ----------------------------------------------------------------------
# auth
# ----------------------------------------------------------------------
def auth_client(api_replies=(), **creds):
    """Returns a client on a mock transport and its request log.

    The token endpoint issues tok1, tok2, ...; API calls return the
    statuses in `api_replies` in order, then 200.
    """
    requests = []
    replies = list(api_replies)

    def handler(request):
        requests.append(request)
        if request.url.host == "auth.test":
            n = sum(r.url.host == "auth.test" for r in requests)
            return httpx2.Response(
                200, json={"access_token": f"tok{n}", "expires_in": 3600}
            )
        return httpx2.Response(replies.pop(0) if replies else 200, json={})

    c = MicroFvsClient("http://api.test", **creds)
    c.session = httpx2.Client(transport=httpx2.MockTransport(handler))
    return c, requests


def token_requests(requests):
    return [r for r in requests if r.url.host == "auth.test"]


def test_no_credentials_sends_no_auth_headers():
    c, requests = auth_client()
    c.healthcheck()
    assert "authorization" not in requests[0].headers
    assert "x-api-key" not in requests[0].headers


@pytest.mark.parametrize("wrap", [str, SecretStr], ids=["str", "SecretStr"])
def test_auth_headers_and_token_request(wrap):
    creds = {**CREDS, "client_secret": wrap(CREDS["client_secret"])}
    creds["api_key"] = wrap(CREDS["api_key"])
    c, requests = auth_client(**creds)
    c.healthcheck()
    token_req, api_req = requests
    assert token_req.headers["authorization"].startswith("Basic ")
    assert token_req.content == (
        b"grant_type=client_credentials&scope=microfvs-api%2Fread"
    )
    assert api_req.headers["authorization"] == "Bearer tok1"
    assert api_req.headers["x-api-key"] == "test-api-key"


def test_credentials_from_env(monkeypatch):
    for name, env_var in CREDENTIAL_ENV_VARS.items():
        monkeypatch.setenv(env_var, CREDS[name])
    c, requests = auth_client()
    c.healthcheck()
    assert requests[-1].headers["x-api-key"] == "test-api-key"


def test_partial_credentials_raise():
    creds = {k: v for k, v in CREDS.items() if k != "token_url"}
    with pytest.raises(ValueError, match="MICROFVS_TOKEN_URL") as err:
        MicroFvsClient("http://api.test", **creds)
    assert "test-client-secret" not in str(err.value)


def test_token_cached_until_near_expiry(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr("microfvs.client.time.monotonic", lambda: now[0])
    c, requests = auth_client(**CREDS)
    c.healthcheck()
    c.healthcheck()
    assert len(token_requests(requests)) == 1
    now[0] += 3600 - 60
    c.healthcheck()
    assert len(token_requests(requests)) == 2


def test_401_retries_once_with_fresh_token():
    c, requests = auth_client([401], **CREDS)
    c.healthcheck()
    assert len(token_requests(requests)) == 2
    assert requests[-1].headers["authorization"] == "Bearer tok2"


def test_repeated_401_raises():
    c, _ = auth_client([401, 401], **CREDS)
    with pytest.raises(httpx2.HTTPStatusError) as err:
        c.healthcheck()
    assert err.value.response.status_code == 401


def test_secrets_not_in_repr():
    c, _ = auth_client(**CREDS)
    c.healthcheck()
    shown = repr(c) + repr(vars(c))
    for secret in ("test-client-secret", "test-api-key", "tok1"):
        assert secret not in shown
