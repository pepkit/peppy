""" Basic smoketests for models """

import logging
import pytest
import pep
from pep.models import AttributeDict, Project


__author__ = "Vince Reuter"
__email__ = "vreuter@virgnia.edu"


_LOGGER = logging.getLogger(__name__)



def pytest_generate_tests(metafunc):
    """ Dynamic test case parameterization. """
    if "funcname" in metafunc.fixturenames:
        metafunc.parametrize(
                argnames="funcname", argvalues=["__repr__", "__str__"])



@pytest.mark.usefixtures("write_project_files")
class AttributeDictRepresentationTests:
    """ Non-fail validation of AttributeDict representations. """


    @pytest.mark.parametrize(
            argnames="data",
            argvalues=[[('CO', 145)], {'CO': {"US-50": [550, 62, 145]}}])
    def test_AttributeDict_representations_smoke(
            self, data, funcname):
        """ Text representation of base AttributeDict doesn't fail. """
        attrdict = AttributeDict(data)
        getattr(attrdict, funcname).__call__()


    def test_Project_representations_smoke(self, proj, funcname):
        """ Representation of Project (AttributeDict subclass) is failsafe. """
        getattr(proj, funcname).__call__()



class ModelCreationSmokeTests:
    """ Smoketests for creation of various types of project-related models. """

    # TODO: migrate these to pytest.raises(None) with 3.1.

    def test_empty_project(self, path_empty_project):
        """ It's unproblematic to create a Project that lacks samples. """
        Project(path_empty_project)



class ModelRepresentationSmokeTests:
    """ Tests for the text representation of important ADTs. """


    @pytest.mark.parametrize(
            argnames="class_name",
            argvalues=[cn for cn in pep.models.__classes__
                       if cn != "Project"])
    def test_repr_smoke(
            self, tmpdir, class_name, basic_instance_data, funcname):
        """ Object representation method successfully returns string. """
        # Note that tmpdir is used when config file needs to be written.
        cls = getattr(pep.models, class_name)
        instance = cls(basic_instance_data)
        func = getattr(instance, funcname)
        result = func.__call__()
        if funcname == "__str__":
            assert class_name in result
        elif funcname == "__repr__":
            assert type(result) is str
        else:
            raise ValueError("Unexpected representation method: {}".
                             format(funcname))
