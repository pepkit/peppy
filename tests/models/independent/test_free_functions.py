""" Tests for module-scoped functions, i.e. those not in a class. """

import copy
import logging
import os
import random
import string
import sys

import pytest

import pep
from pep import Sample, DEV_LOGGING_FMT
from pep.protocol_interface import _import_sample_subtype


__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"



LOCATIONS_OF_SUBTYPE_RELATIVE_TO_PIPELINE = ["above", "below", "parallel"]



def pytest_generate_tests(metafunc):
    """ Customization of this module's test cases. """
    if "location" in metafunc.fixturenames:
        metafunc.parametrize(
                argnames="location",
                argvalues=LOCATIONS_OF_SUBTYPE_RELATIVE_TO_PIPELINE,
                ids=lambda rel_loc:
                " subtypes_relative_location = {} ".format(rel_loc))
    if "has_internal_subtype" in metafunc.fixturenames:
        metafunc.parametrize(
                argnames="has_internal_subtype", argvalues=[False, True],
                ids=lambda has_sub: " internal_subtype = {} ".format(has_sub))



class SampleSubtypeImportTests:
    """ Tests for the lowest-level step in Sample subtype processing. """

    SUBTYPE_1 = "MayBeUsed"
    SUBTYPE_2 = "Unused"


    @pytest.mark.parametrize(
            argnames="subtype_request", argvalues=[None, SUBTYPE_1],
            ids=lambda request: " subtype_request = {} ".format(request))
    def test_single_external_subtype(
            self, location, has_internal_subtype, subtype_request,
            tmpdir, temp_logfile, tmpdir_on_path):
        """ Subtype is inferred iff exactly one's available. """

        external_subtype = subtype_request or self.SUBTYPE_1

        path_pipeline_file, path_subtypes_file = self.write_files(
                pipeline_has_subtype=has_internal_subtype,
                external_subtypes=[external_subtype],
                subtype_module_relative_to_pipeline=location,
                dirpath=tmpdir.strpath)

        observed_subtype = _import_sample_subtype(
                path_pipeline_file, subtype_name=subtype_request)
        try:
            if has_internal_subtype and subtype_request is None:
                assert Sample is observed_subtype
                assert self._validate_basic_sample_reason(temp_logfile)
            else:
                assert external_subtype == observed_subtype.__name__
        except AssertionError:
            self.print_file_contents(
                path_subtypes_file, path_pipeline_file, temp_logfile)
            raise


    @pytest.mark.parametrize(
            argnames="subtype_request", argvalues=[None, SUBTYPE_1, SUBTYPE_2],
            ids=lambda sub_req: " subtype_request = {} ".format(sub_req))
    def test_multiple_external_subtypes(
            self, location, has_internal_subtype, subtype_request,
            tmpdir, temp_logfile, tmpdir_on_path):
        """ With multiple subtypes available, one must be selected. """

        path_pipeline_file, path_subtypes_file = self.write_files(
                pipeline_has_subtype=has_internal_subtype,
                external_subtypes=[self.SUBTYPE_1, self.SUBTYPE_2],
                subtype_module_relative_to_pipeline=location,
                dirpath=tmpdir.strpath)

        observed_subtype = _import_sample_subtype(
                path_pipeline_file, subtype_name=subtype_request)

        if subtype_request is None:
            # We get the base/generic Sample type if we can't do inference.
            assert Sample is observed_subtype

            # Criterion for expected message to validate HOW we got the
            # base/generic Sample type.
            def found_line(msg):
                return "DEBUG" in msg and "subtype cannot be selected" in msg

            # Find the message that indicates the we did in fact get the base/
            # generic sample in the way that was expected.
            with open(temp_logfile, 'r') as tmplog:
                messages = tmplog.readlines()
            try:
                assert any(map(found_line, messages))
            except AssertionError:
                print("Missing expected message: {}".format(messages))
                raise

        else:
            # Request for specific subtype that we defined is found.
            try:
                assert subtype_request == observed_subtype.__name__
            except AssertionError:
                self.print_file_contents(
                        path_subtypes_file, path_pipeline_file,
                        temp_logfile)
                raise


    @staticmethod
    def _validate_basic_sample_reason(
            path_log_file, universal=False,
            criterion=lambda m: "DEBUG" in m and "subtype cannot be selected" in m):
        """
        Assert the reason the base/generic Sample type is being used.

        :param str path_log_file:
        :param bool universal:
        :param function(str) -> bool criterion: whether a single log message
            accords with the expected reason being validated
        :return bool: whether the expected reason indicated by the
            quantification of the given criterion over the collection of
            log messages is satisfied
        """
        with open(path_log_file, 'r') as logfile:
            messages = logfile.readlines()
        quantifier = all if universal else any
        return quantifier(map(criterion, messages))


    def write_files(
            self, pipeline_has_subtype, external_subtypes, 
            subtype_module_relative_to_pipeline, dirpath):
        """
        Create files for pipeline module and external subtypes module.
        
        :param bool pipeline_has_subtype: whether to also define a Sample
            subtype within the pipeline module itself
        :param Iterable[str] external_subtypes: collection of names of
            Sample subtypes to defined in the external subtypes file
        :param str subtype_module_relative_to_pipeline: text indicating
            how the external subtypes module should be created on disk
            relative to the file for the pipeline module itself
        :param str dirpath: path to parent folder for the pipeline and
            subtypes module files
        :return (str, str): pair of paths to files that were written, to the
            pipeline module file and to the subtypes module file
        """

        # Randomize names to prevent collisions of imports (sys.modules).
        pipeline_name_suffix = "".join(
                [random.choice(string.ascii_lowercase) for _ in range(15)])
        pipeline_modname = "pipe{}".format(pipeline_name_suffix)
        subtypes_modname_suffix = "".join(
                [random.choice(string.ascii_lowercase) for _ in range(15)])
        subtypes_modname = "subtypes{}".format(subtypes_modname_suffix)


        # The domain over which to indicate the relative position of
        # the files is restricted to prevent unexpected behavior.
        if subtype_module_relative_to_pipeline not in \
                LOCATIONS_OF_SUBTYPE_RELATIVE_TO_PIPELINE:
            raise ValueError(
                "Unexpected location for subtype module relative to "
                "pipeline; got {}, expecting one of {}".format(
                    subtype_module_relative_to_pipeline,
                    LOCATIONS_OF_SUBTYPE_RELATIVE_TO_PIPELINE))

        submodule_name = "".join(
                [random.choice(string.ascii_lowercase) for _ in range(20)])
        subfolder_path = os.path.join(dirpath, submodule_name)
        os.makedirs(subfolder_path)

        # Independent of the file structure.
        name_pipeline_file = "{}.py".format(pipeline_modname)
        name_subtypes_file = "{}.py".format(subtypes_modname)

        # The filesystem position of the subtypes module file relative to
        # the pipeline module file determines the paths and how to write
        # the statement to import the subtypes module into the pipeline module.
        if subtype_module_relative_to_pipeline == "below":
            # On disk, subtypes module is "below" pipeline module.
            # With the parent folder added to sys.path, we can refer to the
            # target package + module in this way if we designate a subpackage.
            # All we need to do is create the package initialization file.
            with open(os.path.join(dirpath, "__init__.py"), 'w'):
                pass
            with open(os.path.join(subfolder_path, "__init__.py"), 'w'):
                pass
            import_prefix = \
                "from {}.{}".format(submodule_name, subtypes_modname)
            path_pipe_file = os.path.join(dirpath, name_pipeline_file)
            path_subtypes_file = os.path.join(
                subfolder_path, name_subtypes_file)
        else:
            import_prefix = "from {}".format(subtypes_modname)
            if subtype_module_relative_to_pipeline == "parallel":
                # On disk, subtypes module file is "next to" pipeline module.
                path_pipe_file = os.path.join(dirpath, name_pipeline_file)
                path_subtypes_file = os.path.join(dirpath, name_subtypes_file)
            else:
                # On disk, subtypes module file is "above" pipeline module.
                path_pipe_file = os.path.join(
                        subfolder_path, name_pipeline_file)
                path_subtypes_file = os.path.join(dirpath, name_subtypes_file)

        # Write the subtypes module file.
        with open(path_subtypes_file, 'w') as subtypes_file:
            subtypes_file.write("from pep import Sample\n\n")
            subtypes_file.write(build_subtype_lines(external_subtypes))

        # Write the pipeline module file.
        imports = ["{} import {}\n".format(import_prefix, subtype_name)
                   for subtype_name in external_subtypes]
        with open(path_pipe_file, 'w') as pipe_file:
            for import_statement in imports:
                pipe_file.write(import_statement)
            # Include a subtype definition with the pipeline itself as desired.
            if pipeline_has_subtype:
                pipe_file.write("from pep import Sample\n\n")
                pipe_file.write(build_subtype_lines("InternalPipelineSample"))

        return path_pipe_file, path_subtypes_file

    
    @pytest.fixture(scope="function")
    def temp_logfile(self, request, tmpdir):
        """
        Temporarily capture in a file logging information from pep models.

        :param request: test case using this fixture
        :param tmpdir: temporary directory fixture
        :return str: path to the file in which logging information is captured
        """

        target_level = logging.DEBUG

        # Retain original logger level to reset.
        original_loglevel = pep._LOGGER.getEffectiveLevel()

        # Create the handler with appropriate level and formatter for test.
        logfile = os.path.join(tmpdir.strpath, "logfile.txt")
        handler = logging.FileHandler(logfile, mode='w')
        formatter = logging.Formatter(DEV_LOGGING_FMT)
        handler.setFormatter(formatter)
        handler.setLevel(target_level)

        # Add the handler to the relevant logger.
        pep._LOGGER.setLevel(target_level)
        pep._LOGGER.handlers.append(handler)
        
        def reset_logger():
            pep._LOGGER.setLevel(original_loglevel)
            del pep._LOGGER.handlers[-1]

        # Restore the logger when the test case finishes, and provide the
        # test case with the path to the file to which logs will be written
        # so that the test case can make assertions about the message content.
        request.addfinalizer(reset_logger)
        return logfile


    @pytest.fixture(scope="function")
    def tmpdir_on_path(self, request, tmpdir):
        # Ordinarily, presence on path of the subtypes module would
        # be needed / assumed to be present for what's under test to
        # work, that the subtype(s) need not live in the exact same
        # module that defines the pipeline. Instead, we autouse the temporary
        # directory-on-path fixture to simulate that effect.
        dirpath = tmpdir.strpath
        path_copy = copy.copy(sys.path)
        sys.path.append(dirpath)
        def restore_sys_path():
            sys.path = path_copy
        request.addfinalizer(restore_sys_path)


    @staticmethod
    def print_file_contents(subtypes_file, pipeline_file, logfile):
        """ When an assertion fails, get more information. """
        with open(subtypes_file, 'r') as f:
            subtypes_contents = "".join(f.readlines())
        with open(pipeline_file, 'r') as f:
            pipeline_contents = "".join(f.readlines())
        with open(logfile, 'r') as f:
            logfile_contents = "".join(f.readlines())
        print("")
        print("Subtypes file:")
        print(subtypes_contents)
        print("")
        print("Pipeline file:")
        print(pipeline_contents)
        print("")
        print("Logs:")
        print(logfile_contents)
        print("")



def build_subtype_lines(subtype_names):
    """
    Create text that defines minimal version of Sample subtypes.

    Given a collection of class names, create the raw text that defines each
    of them as a Sample subtype.

    :param Iterable[str] subtype_names: collection of class names, i.e. a
        name for each of the Sample subtypes to define
    :return str: the raw text that is used to define the entire collection
        of Sample subtypes, named as indicated by the argument provided
    """
    if isinstance(subtype_names, str):
        subtype_names = [subtype_names]
    else:
        subtype_names = list(subtype_names)
    return "\n\n".join(map(subtype_def_text, subtype_names))



def subtype_def_text(subtype_name):
    """
    Create the definition text for a single Sample subtype.

    :param str subtype_name:
    :return str: text that would be written to define a single Sample subtype
    """
    template = "class {sub}({sup}):\n" \
               "\tdef __init__(self, *args, **kwargs):\n" \
               "\t\tsuper({sub}, self).__init__(*args, **kwargs)"
    return template.format(sub=subtype_name, sup=Sample.__name__)
