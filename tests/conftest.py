import pytest

from pephubclient.pephub_oauth.models import InitializeDeviceCodeResponse


@pytest.fixture()
def device_code_return():
    device_code = "asdf2345"
    return InitializeDeviceCodeResponse(
        device_code=device_code,
        auth_url=f"any_base_url/auth/device/login/{device_code}",
    )


@pytest.fixture()
def test_raw_pep_return():
    sample_prj = {
        "config": {
            "This": "is config",
            "description": "desc",
            "name": "sample name",
        },
        "subsample_list": [],
        "sample_list": [
            {"time": "0", "file_path": "source1", "sample_name": "pig_0h"},
            {"time": "1", "file_path": "source1", "sample_name": "pig_1h"},
            {"time": "0", "file_path": "source1", "sample_name": "frog_0h"},
        ],
    }
    return sample_prj


@pytest.fixture
def requests_get_mock(mocker):
    return mocker.patch("requests.get")


@pytest.fixture
def input_return_mock(monkeypatch):
    return monkeypatch.setattr("builtins.input", lambda: None)


@pytest.fixture
def test_jwt():
    return (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJsb2dpbiI6InJhZmFsc3RlcGllbiIsImlkIjo0MzkyNjUyMiwib3JnYW5pemF0aW9ucyI6bnVsbH0."
        "mgBP-7x5l9cqufhzdVi0OFA78pkYDEymwPFwud02BAc"
    )
