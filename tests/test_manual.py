from pephubclient.pephubclient import PEPHubClient
import pytest


@pytest.mark.skip(reason="Manual test")
class TestViewsManual:
    def test_get(self):
        ff = PEPHubClient().view.get(
            "databio",
            "bedset1",
            "default",
            "test_view",
        )
        print(ff)

    def test_create(self):
        PEPHubClient().view.create(
            "databio",
            "bedset1",
            "default",
            "test_view",
            sample_list=["orange", "grape1", "apple1"],
        )

    def test_delete(self):
        PEPHubClient().view.delete(
            "databio",
            "bedset1",
            "default",
            "test_view",
        )

    def test_add_sample(self):
        PEPHubClient().view.add_sample(
            "databio",
            "bedset1",
            "default",
            "test_view",
            "name",
        )

    def test_delete_sample(self):
        PEPHubClient().view.remove_sample(
            "databio",
            "bedset1",
            "default",
            "test_view",
            "name",
        )


@pytest.mark.skip(reason="Manual test")
class TestSamplesManual:
    def test_manual(self):
        ff = PEPHubClient().sample.get(
            "databio",
            "bedset1",
            "default",
            "grape1",
        )
        ff

    def test_update(self):
        ff = PEPHubClient().sample.get(
            "databio",
            "bedset1",
            "default",
            "newf",
        )
        ff.update({"shefflab": "test1"})
        ff["sample_type"] = "new_type"
        PEPHubClient().sample.update(
            "databio",
            "bedset1",
            "default",
            "newf",
            sample_dict=ff,
        )

    def test_add(self):
        ff = {
            "genome": "phc_test1",
            "sample_type": "phc_test",
        }
        PEPHubClient().sample.create(
            "databio",
            "bedset1",
            "default",
            "new_2222",
            overwrite=False,
            sample_dict=ff,
        )

    def test_delete(self):
        PEPHubClient().sample.remove(
            "databio",
            "bedset1",
            "default",
            "new_2222",
        )
