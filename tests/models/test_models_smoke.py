""" Basic smoketests for models """

import pytest
from looper.models import AttributeDict, Project

__author__ = "Vince Reuter"
__email__ = "vreuter@virgnia.edu"



def pytest_generate_tests(metafunc):
    if metafunc.cls == AttributeDictRepresentationSmokeTests:
        metafunc.parametrize(argnames="representation_method",
                             argvalues=["__repr__", "__str__"])



@pytest.mark.usefixtures("write_project_files")
class AttributeDictRepresentationSmokeTests:
    """ Non-fail validation of AttributeDict representations. """


    @pytest.mark.parametrize(
            argnames="data",
            argvalues=[[('CO', 145)], {'CO': {"US-50": [550, 62, 145]}}])
    def test_AttributeDict_representations(
            self, data, representation_method):
        """ Text representation of base AttributeDict doesn't fail. """
        attrdict = AttributeDict(data)
        getattr(attrdict, representation_method).__call__()


    def test_Project_representations(self, proj, representation_method):
        """ Representation of Project (AttributeDict subclass) is failsafe. """
        getattr(proj, representation_method).__call__()
