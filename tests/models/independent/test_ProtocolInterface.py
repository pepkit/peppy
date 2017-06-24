""" Tests for ProtocolInterface, for Project/PipelineInterface interaction. """

import os
import pytest
import yaml
from looper.models import ProtocolInterface


__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"



def _write_config_data(conf_data, dirpath):
    """
    
    :param conf_data: 
    :param dirpath: 
    :return: 
    """
    filepath = os.path.join(dirpath, "pipeline_interface.yaml")
    with open(filepath, 'w') as conf_file:
        yaml.safe_dump(conf_data, conf_file)
    return filepath



@pytest.fixture(scope="function")
def path_config_file(request, tmpdir):
    conf_data = request.getfixturevalue("atacseq_piface_data")
    full_conf_data = {"protocol_mapping": {"ATAC": "ATACSeq.py"},
                      "pipelines": conf_data}
    return _write_config_data(full_conf_data, dirpath=tmpdir.strpath)



class PipelinePathResolutionTests:
    """ Project requests pipeline information via an interface key. """

    PIPELINE_KEY = "ATACSeq.py"

    def test_no_path(self, atacseq_piface_data, path_config_file):
        proto_iface = ProtocolInterface(path_config_file)
        config_dirpath = os.path.dirname(path_config_file)
        expected_pipe_path = os.path.join(config_dirpath, self.PIPELINE_KEY)
        _, full_pipe_path, _ = \
                proto_iface.pipeline_key_to_path(self.PIPELINE_KEY)
        assert expected_pipe_path == full_pipe_path


    @pytest.mark.skip("Not implemented")
    def test_relative_path(self, piface_config):
        pass


    @pytest.mark.skip("Not implemented")
    def test_absolute_path(self, piface_config):
        pass


    @pytest.mark.skip("Not implemented")
    def test_pipeline_interface_path(self, piface_config):
        pass



@pytest.mark.skip("Not implemented")
class ProtocolInterfacePipelineSampleSubtypeTests:
    """ ProtocolInterface attempts import of pipeline-specific Sample. """
    pass
