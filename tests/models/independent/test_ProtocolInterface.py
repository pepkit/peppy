""" Tests for ProtocolInterface, for Project/PipelineInterface interaction. """

import pytest
from looper.models import ProtocolInterface


__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"



@pytest.mark.skip("Not implemented")
class PipelinePathResolutionTests:
    """ Project requests pipeline information via an interface key. """


    def test_no_path(self, piface_config_bundles):
        pass


    def test_relative_path(self, piface_config_bundles):
        pass


    def test_absolute_path(self, piface_config_bundles):
        pass


    def test_pipeline_interface_path(self, piface_config_bundles):
        pass



@pytest.mark.skip("Not implemented")
class ProtocolInterfacePipelineSampleSubtypeTests:
    """ ProtocolInterface attempts import of pipeline-specific Sample. """
    pass
