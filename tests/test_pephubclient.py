import os
from unittest.mock import Mock

import pytest

from pephubclient.exceptions import ResponseError
from pephubclient.pephubclient import PEPHubClient
from pephubclient.helpers import is_registry_path

SAMPLE_PEP = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tests",
    "data",
    "sample_pep",
    "subsamp_config.yaml",
)


class TestSmoke:
    def test_login(self, mocker, device_code_return, test_jwt):
        """
        Test if device login request was sent to pephub
        """
        requests_mock = mocker.patch(
            "requests.request",
            return_value=Mock(content=device_code_return, status_code=200),
        )
        pephub_response_mock = mocker.patch(
            "pephubclient.pephub_oauth.pephub_oauth.PEPHubAuth._handle_pephub_response",
            return_value=device_code_return,
        )
        pephub_exchange_code_mock = mocker.patch(
            "pephubclient.pephub_oauth.pephub_oauth.PEPHubAuth._exchange_device_code_on_token",
            return_value=test_jwt,
        )

        pathlib_mock = mocker.patch(
            "pephubclient.files_manager.FilesManager.save_jwt_data_to_file"
        )

        PEPHubClient().login()

        assert requests_mock.called
        assert pephub_response_mock.called
        assert pephub_exchange_code_mock.called
        assert pathlib_mock.called

    def test_logout(self, mocker):
        os_remove_mock = mocker.patch("os.remove")
        PEPHubClient().logout()

        assert os_remove_mock.called

    def test_pull(self, mocker, test_jwt, test_raw_pep_return):
        jwt_mock = mocker.patch(
            "pephubclient.files_manager.FilesManager.load_jwt_data_from_file",
            return_value=test_jwt,
        )
        requests_mock = mocker.patch(
            "requests.request",
            return_value=Mock(content="some return", status_code=200),
        )
        mocker.patch(
            "pephubclient.helpers.RequestManager.decode_response",
            return_value=test_raw_pep_return,
        )
        save_yaml_mock = mocker.patch(
            "pephubclient.files_manager.FilesManager.save_yaml"
        )
        save_sample_mock = mocker.patch(
            "pephubclient.files_manager.FilesManager.save_pandas"
        )
        mocker.patch("pephubclient.files_manager.FilesManager.create_project_folder")

        PEPHubClient().pull("some/project")

        assert jwt_mock.called
        assert requests_mock.called
        assert save_yaml_mock.called
        assert save_sample_mock.called

    @pytest.mark.parametrize(
        "status_code, expected_error_message",
        [
            (
                404,
                "File does not exist, or you are unauthorized.",
            ),
            (
                500,
                "Internal server error. Unexpected return value. Error: 500",
            ),
        ],
    )
    def test_pull_with_pephub_error_response(
        self, mocker, test_jwt, status_code, expected_error_message
    ):
        mocker.patch(
            "pephubclient.files_manager.FilesManager.load_jwt_data_from_file",
            return_value=test_jwt,
        )
        mocker.patch(
            "requests.request",
            return_value=Mock(
                content=b'{"detail": "Some error message"}', status_code=status_code
            ),
        )

        with pytest.raises(ResponseError) as e:
            PEPHubClient().pull("some/project")

        assert e.value.message == expected_error_message

    def test_push(self, mocker, test_jwt):
        requests_mock = mocker.patch(
            "requests.request", return_value=Mock(status_code=202)
        )

        PEPHubClient().push(
            SAMPLE_PEP,
            namespace="s_name",
            name="name",
        )

        assert requests_mock.called

    @pytest.mark.parametrize(
        "status_code, expected_error_message",
        [
            (
                409,
                "Project already exists. Set force to overwrite project.",
            ),
            (
                401,
                "Unauthorized! Failure in uploading project.",
            ),
            (233, "Unexpected Response Error."),
        ],
    )
    def test_push_with_pephub_error_response(
        self, mocker, status_code, expected_error_message
    ):
        mocker.patch("requests.request", return_value=Mock(status_code=status_code))
        with pytest.raises(ResponseError, match=expected_error_message):
            PEPHubClient().push(
                SAMPLE_PEP,
                namespace="s_name",
                name="name",
            )

    def test_search_prj(self, mocker):
        return_value = {
            "count": 1,
            "limit": 100,
            "offset": 0,
            "results": [
                {
                    "namespace": "namespace1",
                    "name": "basic",
                    "tag": "default",
                    "is_private": False,
                    "number_of_samples": 2,
                    "description": "None",
                    "last_update_date": "2023-08-27 19:07:31.552861+00:00",
                    "submission_date": "2023-08-27 19:07:31.552858+00:00",
                    "digest": "08cbcdbf4974fc84bee824c562b324b5",
                    "pep_schema": "random_schema_name",
                    "pop": False,
                    "stars_number": 0,
                    "forked_from": None,
                }
            ],
            "session_info": None,
            "can_edit": False,
        }
        mocker.patch(
            "requests.request",
            return_value=Mock(content=return_value, status_code=200),
        )
        mocker.patch(
            "pephubclient.helpers.RequestManager.decode_response",
            return_value=return_value,
        )

        return_value = PEPHubClient().find_project(namespace="namespace1")
        assert return_value.count == 1
        assert len(return_value.results) == 1


class TestHelpers:
    @pytest.mark.parametrize(
        "input_str, expected_output",
        [
            (
                "databio/pep:default",
                True,
            ),
            (
                "pephub.databio.org::databio/pep:default",
                True,
            ),
            (
                "pephub.databio.org://databio/pep:default",
                True,
            ),
            (
                "databio/pep",
                True,
            ),
            (
                "databio/pep/default",
                False,
            ),
            (
                "some/random/path/to.yaml",
                False,
            ),
            (
                "path_to.csv",
                False,
            ),
            (
                "this/is/path/to.csv",
                False,
            ),
        ],
    )
    def test_is_registry_path(self, input_str, expected_output):
        assert is_registry_path(input_str) is expected_output


class TestSamples:
    def test_get(self, mocker):
        return_value = {
            "genome": "phc_test1",
            "sample_type": "phc_test",
            "sample_name": "gg1",
        }
        mocker.patch(
            "requests.request",
            return_value=Mock(content=return_value, status_code=200),
        )
        mocker.patch(
            "pephubclient.helpers.RequestManager.decode_response",
            return_value=return_value,
        )
        return_value = PEPHubClient().sample.get(
            "test_namespace",
            "taest_name",
            "default",
            "gg1",
        )
        assert return_value == return_value

    @pytest.mark.parametrize(
        "status_code, expected_error_message",
        [
            (
                404,
                "Sample does not exist.",
            ),
            (
                500,
                "Internal server error. Unexpected return value.",
            ),
            (
                403,
                "Unexpected return value. Error: 403",
            ),
        ],
    )
    def test_sample_get_with_pephub_error_response(
        self, mocker, status_code, expected_error_message
    ):
        mocker.patch("requests.request", return_value=Mock(status_code=status_code))
        with pytest.raises(ResponseError, match=expected_error_message):
            PEPHubClient().sample.get(
                "test_namespace",
                "taest_name",
                "default",
                "gg1",
            )

    @pytest.mark.parametrize(
        "prj_dict",
        [
            {"genome": "phc_test1", "sample_type": "phc_test", "sample_name": "gg1"},
            {"genome": "phc_test1", "sample_type": "phc_test"},
        ],
    )
    def test_create(self, mocker, prj_dict):
        return_value = prj_dict
        mocker_obj = mocker.patch(
            "requests.request",
            return_value=Mock(content=return_value, status_code=202),
        )

        PEPHubClient().sample.create(
            "test_namespace",
            "taest_name",
            "default",
            "gg1",
            sample_dict=return_value,
        )
        assert mocker_obj.called

    @pytest.mark.parametrize(
        "status_code, expected_error_message",
        [
            (
                404,
                "does not exist.",
            ),
            (
                409,
                "already exists. Set overwrite to True to overwrite sample.",
            ),
            (
                500,
                "Unexpected return value.",
            ),
        ],
    )
    def test_sample_create_with_pephub_error_response(
        self, mocker, status_code, expected_error_message
    ):
        mocker.patch("requests.request", return_value=Mock(status_code=status_code))
        with pytest.raises(ResponseError, match=expected_error_message):
            PEPHubClient().sample.create(
                "test_namespace",
                "taest_name",
                "default",
                "gg1",
                sample_dict={
                    "genome": "phc_test1",
                    "sample_type": "phc_test",
                    "sample_name": "gg1",
                },
            )

    def test_delete(self, mocker):
        mocker_obj = mocker.patch(
            "requests.request",
            return_value=Mock(status_code=202),
        )

        PEPHubClient().sample.remove(
            "test_namespace",
            "taest_name",
            "default",
            "gg1",
        )
        assert mocker_obj.called

    @pytest.mark.parametrize(
        "status_code, expected_error_message",
        [
            (
                404,
                "does not exist.",
            ),
            (
                500,
                "Unexpected return value.",
            ),
        ],
    )
    def test_sample_delete_with_pephub_error_response(
        self, mocker, status_code, expected_error_message
    ):
        mocker.patch("requests.request", return_value=Mock(status_code=status_code))
        with pytest.raises(ResponseError, match=expected_error_message):
            PEPHubClient().sample.remove(
                "test_namespace",
                "taest_name",
                "default",
                "gg1",
            )

    def test_update(self, mocker):
        mocker_obj = mocker.patch(
            "requests.request",
            return_value=Mock(status_code=202),
        )

        PEPHubClient().sample.update(
            "test_namespace",
            "taest_name",
            "default",
            "gg1",
            sample_dict={
                "genome": "phc_test1",
                "sample_type": "phc_test",
                "new_col": "column",
            },
        )
        assert mocker_obj.called

    @pytest.mark.parametrize(
        "status_code, expected_error_message",
        [
            (
                404,
                "does not exist.",
            ),
            (
                500,
                "Unexpected return value.",
            ),
        ],
    )
    def test_sample_update_with_pephub_error_response(
        self, mocker, status_code, expected_error_message
    ):
        mocker.patch("requests.request", return_value=Mock(status_code=status_code))
        with pytest.raises(ResponseError, match=expected_error_message):
            PEPHubClient().sample.update(
                "test_namespace",
                "taest_name",
                "default",
                "gg1",
                sample_dict={
                    "genome": "phc_test1",
                    "sample_type": "phc_test",
                    "new_col": "column",
                },
            )


class TestViews:
    def test_get(self, mocker, test_raw_pep_return):
        return_value = test_raw_pep_return
        mocker.patch(
            "requests.request",
            return_value=Mock(content=return_value, status_code=200),
        )
        mocker.patch(
            "pephubclient.helpers.RequestManager.decode_response",
            return_value=return_value,
        )

        return_value = PEPHubClient().view.get(
            "test_namespace",
            "taest_name",
            "default",
            "gg1",
        )
        assert return_value == return_value

    @pytest.mark.parametrize(
        "status_code, expected_error_message",
        [
            (
                404,
                "does not exist.",
            ),
            (
                500,
                "Internal server error.",
            ),
        ],
    )
    def test_view_get_with_pephub_error_response(
        self, mocker, status_code, expected_error_message
    ):
        mocker.patch("requests.request", return_value=Mock(status_code=status_code))
        with pytest.raises(ResponseError, match=expected_error_message):
            PEPHubClient().view.get(
                "test_namespace",
                "taest_name",
                "default",
                "gg1",
            )

    def test_create(self, mocker):
        mocker_obj = mocker.patch(
            "requests.request",
            return_value=Mock(status_code=202),
        )

        PEPHubClient().view.create(
            "test_namespace",
            "taest_name",
            "default",
            "gg1",
            sample_list=["sample1", "sample2"],
        )
        assert mocker_obj.called

    @pytest.mark.parametrize(
        "status_code, expected_error_message",
        [
            (
                404,
                "does not exist.",
            ),
            (
                409,
                "already exists in the project.",
            ),
        ],
    )
    def test_view_create_with_pephub_error_response(
        self, mocker, status_code, expected_error_message
    ):
        mocker.patch("requests.request", return_value=Mock(status_code=status_code))
        with pytest.raises(ResponseError, match=expected_error_message):
            PEPHubClient().view.create(
                "test_namespace",
                "taest_name",
                "default",
                "gg1",
                sample_list=["sample1", "sample2"],
            )

    def test_delete(self, mocker):
        mocker_obj = mocker.patch(
            "requests.request",
            return_value=Mock(status_code=202),
        )

        PEPHubClient().view.delete(
            "test_namespace",
            "taest_name",
            "default",
            "gg1",
        )
        assert mocker_obj.called

    @pytest.mark.parametrize(
        "status_code, expected_error_message",
        [
            (
                404,
                "does not exist.",
            ),
            (
                401,
                "You are unauthorized to delete this view.",
            ),
        ],
    )
    def test_view_delete_with_pephub_error_response(
        self, mocker, status_code, expected_error_message
    ):
        mocker.patch("requests.request", return_value=Mock(status_code=status_code))
        with pytest.raises(ResponseError, match=expected_error_message):
            PEPHubClient().view.delete(
                "test_namespace",
                "taest_name",
                "default",
                "gg1",
            )

    def test_add_sample(self, mocker):
        mocker_obj = mocker.patch(
            "requests.request",
            return_value=Mock(status_code=202),
        )

        PEPHubClient().view.add_sample(
            "test_namespace",
            "taest_name",
            "default",
            "gg1",
            "sample1",
        )
        assert mocker_obj.called

    def test_delete_sample(self, mocker):
        mocker_obj = mocker.patch(
            "requests.request",
            return_value=Mock(status_code=202),
        )

        PEPHubClient().view.remove_sample(
            "test_namespace",
            "taest_name",
            "default",
            "gg1",
            "sample1",
        )
        assert mocker_obj.called


###


# test add sample:
# 1. add correct 202
# 2. add existing 409
# 3. add with sample_name
# 4. add without sample_name
# 5. add with overwrite
# 6. add to unexisting project 404

# delete sample:
# 1. delete existing 202
# 2. delete unexisting 404

# get sample:
# 1. get existing 200
# 2. get unexisting 404
# 3. get with raw 200
# 4. get from unexisting project 404

# update sample:
# 1. update existing 202
# 2. update unexisting sample 404
# 3. update unexisting project 404
