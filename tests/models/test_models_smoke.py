""" Basic smoketests for models """

import inspect
import logging
import pytest
import looper
from looper.models import AttributeDict


__author__ = "Vince Reuter"
__email__ = "vreuter@virgnia.edu"


_LOGGER = logging.getLogger(__name__)



def pytest_generate_tests(metafunc):
    """ Dynamic test case parameterization. """
    if metafunc.cls == AttributeDictRepresentationSmokeTests:
        metafunc.parametrize(argnames="representation_method",
                             argvalues=["__repr__", "__str__"])
    elif metafunc.cls == ObjectRepresentationSmokeTests:
        metafunc.parametrize(argnames="class_name",
                             argvalues=looper.models.__classes__)
        metafunc.parametrize(argnames="method_name", argvalues=["__repr__"])



class ObjectRepresentationSmokeTests:
    """ Tests for the text representation of important ADTs. """


    def test_implements_repr_smoke(self, class_name, method_name):
        """ Each important ADT must implement a representation method. """

        # Attempt a control assertion, that a subclass that doesn't override
        # the given method of its superclass, uses the superclass version of
        # the function in question.
        class ObjectSubclass(object):
            def __init__(self):
                super(ObjectSubclass, self).__init__()
        try:
            subclass_version = getattr(ObjectSubclass, "__repr__")
            superclass_version = getattr(object, method_name)
        except AttributeError:
            _LOGGER.debug("No object subclass vs. object validation for "
                          "method: '%s'", method_name)
        else:
            assert subclass_version is superclass_version

        # Make the actual assertion of interest.
        adt = getattr(looper.models, class_name)
        assert getattr(adt, method_name) != \
               getattr(adt.__bases__[0], method_name)


    def test_repr_smoke(self, class_name, method_name):
        """ Object representation method successfully returns string. """
        # TODO: with pytest.raises(None) in 3.1+
        assert str is type(getattr(class_name, method_name).__call__())



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
