""" Tests for ProtocolInterface, for Project/PipelineInterface interaction. """

import inspect
import itertools
import logging
import os
import sys
if sys.version_info < (3, ):
    import __builtin__ as builtins
else:
    import builtins

import mock
import pytest
import yaml

from looper import models, DEV_LOGGING_FMT
from looper.models import ProtocolInterface, Sample
from looper.utils import import_from_source


__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"


ATAC_PROTOCOL_NAME = "ATAC"


class CustomExceptionA(Exception):
    def __init__(self, *args):
        super(CustomExceptionA, self).__init__(*args)

class CustomExceptionB(Exception):
    def __init__(self, *args):
        super(CustomExceptionB, self).__init__(*args)

CUSTOM_EXCEPTIONS = [CustomExceptionA, CustomExceptionB]


# Test case parameterization, but here for import locality and
# to reduce clutter in the pararmeterization declaration.
_, BUILTIN_EXCEPTIONS_WITHOUT_REQUIRED_ARGUMENTS = \
        list(map(list, zip(*inspect.getmembers(
                builtins, lambda o: inspect.isclass(o) and
                                       issubclass(o, BaseException) and
                                       not issubclass(o, UnicodeError)))))


def pytest_generate_tests(metafunc):
    """ Customization of this module's test cases. """
    if "subtypes_section_spec_type" in metafunc.fixturenames:
        # Subtypes section can be raw string or mapping.
        metafunc.parametrize(argnames="subtypes_section_spec_type",
                             argvalues=[str, dict])



@pytest.fixture(scope="function")
def path_config_file(request, tmpdir, atac_pipe_name):
    """
    Write PipelineInterface configuration data to disk.

    Grab the data from the test case's appropriate fixture. Also check the
    test case parameterization for pipeline path specification, adding it to
    the configuration data before writing to disk if the path specification is
    present

    :param pytest._pytest.fixtures.SubRequest request: test case requesting
        this fixture
    :param py.path.local.LocalPath tmpdir: temporary directory fixture
    :param str atac_pipe_name: name/key for ATAC-Seq pipeline; this should
        also be used by the requesting test case if a path is to be added;
        separating the name from the folder path allows parameterization of
        the test case in terms of folder path, with pipeline name appended
        after the fact (that is, the name fixture can't be used in the )
    :return str: path to the configuration file written
    """
    conf_data = request.getfixturevalue("atacseq_piface_data")
    if "pipe_path" in request.fixturenames:
        pipeline_dirpath = request.getfixturevalue("pipe_path")
        pipe_path = os.path.join(pipeline_dirpath, atac_pipe_name)
        # Pipeline key/name is mapped to the interface data; insert path in
        # that Mapping, not at the top level, in which name/key is mapped to
        # interface data bundle.
        for iface_bundle in conf_data.values():
            iface_bundle["path"] = pipe_path
    return _write_config_data(protomap={ATAC_PROTOCOL_NAME: atac_pipe_name},
                              conf_data=conf_data, dirpath=tmpdir.strpath)



class PipelinePathResolutionTests:
    """ Project requests pipeline information via an interface key. """


    def test_no_path(self, atacseq_piface_data,
                     path_config_file, atac_pipe_name):
        """ Without explicit path, pipeline is assumed parallel to config. """

        piface = ProtocolInterface(path_config_file)

        # The pipeline is assumed to live alongside its configuration file.
        config_dirpath = os.path.dirname(path_config_file)
        expected_pipe_path = os.path.join(config_dirpath, atac_pipe_name)

        _, full_pipe_path, _ = \
                piface.finalize_pipeline_key_and_paths(atac_pipe_name)
        assert expected_pipe_path == full_pipe_path


    def test_relpath_with_dot_becomes_absolute(
            self, tmpdir, atac_pipe_name, atacseq_piface_data):
        """ Leading dot drops from relative path, and it's made absolute. """
        path_parts = ["relpath", "to", "pipelines", atac_pipe_name]
        sans_dot_path = os.path.join(*path_parts)
        pipe_path = os.path.join(".", sans_dot_path)
        atacseq_piface_data[atac_pipe_name]["path"] = pipe_path

        exp_path = os.path.join(tmpdir.strpath, sans_dot_path)

        path_config_file = _write_config_data(
                protomap={ATAC_PROTOCOL_NAME: atac_pipe_name},
                conf_data=atacseq_piface_data, dirpath=tmpdir.strpath)
        piface = ProtocolInterface(path_config_file)
        _, obs_path, _ = piface.finalize_pipeline_key_and_paths(atac_pipe_name)
        # Dot may remain in path, so assert equality of absolute paths.
        assert os.path.abspath(exp_path) == os.path.abspath(obs_path)


    @pytest.mark.parametrize(
            argnames="pipe_path", argvalues=["relative/pipelines/path"])
    def test_non_dot_relpath_becomes_absolute(
            self, atacseq_piface_data, path_config_file,
            tmpdir, pipe_path, atac_pipe_name):
        """ Relative pipeline path is made absolute when requested by key. """
        # TODO: constant-ify "path" and "ATACSeq.py", as well as possibly "pipelines"
        # and "protocol_mapping" section names of PipelineInterface
        exp_path = os.path.join(
                tmpdir.strpath, pipe_path, atac_pipe_name)
        piface = ProtocolInterface(path_config_file)
        _, obs_path, _ = piface.finalize_pipeline_key_and_paths(atac_pipe_name)
        assert exp_path == obs_path


    @pytest.mark.parametrize(
            argnames=["pipe_path", "expected_path_base"],
            argvalues=[(os.path.join("$HOME", "code-base-home", "biopipes"),
                        os.path.join(os.path.expandvars("$HOME"),
                                "code-base-home", "biopipes")),
                       (os.path.join("~", "bioinformatics-pipelines"),
                        os.path.join(os.path.expanduser("~"),
                                     "bioinformatics-pipelines"))])
    def test_absolute_path(
            self, atacseq_piface_data, path_config_file, tmpdir, pipe_path,
            expected_path_base, atac_pipe_name):
        """ Absolute path regardless of variables works as pipeline path. """
        exp_path = os.path.join(
                tmpdir.strpath, expected_path_base, atac_pipe_name)
        piface = ProtocolInterface(path_config_file)
        _, obs_path, _ = piface.finalize_pipeline_key_and_paths(atac_pipe_name)
        assert exp_path == obs_path


    @pytest.mark.xfail(
            condition=models._LOGGER.getEffectiveLevel() < logging.WARN,
            reason="Insufficient logging level to capture warning message: {}".
                   format(models._LOGGER.getEffectiveLevel()))
    @pytest.mark.parametrize(
        argnames="pipe_path",
        argvalues=["nonexistent.py", "path/to/missing.py",
                   "/abs/path/to/mythical"])
    def test_warns_about_nonexistent_pipeline_script_path(
            self, atacseq_piface_data, path_config_file,
            tmpdir, pipe_path, atac_pipe_name):
        """ Nonexistent, resolved pipeline script path generates warning. """
        name_log_file = "temp-test-log.txt"
        path_log_file = os.path.join(tmpdir.strpath, name_log_file)
        temp_hdlr = logging.FileHandler(path_log_file, mode='w')
        fmt = logging.Formatter(DEV_LOGGING_FMT)
        temp_hdlr.setFormatter(fmt)
        temp_hdlr.setLevel(logging.WARN)
        models._LOGGER.handlers.append(temp_hdlr)
        pi = ProtocolInterface(path_config_file)
        pi.finalize_pipeline_key_and_paths(atac_pipe_name)
        with open(path_log_file, 'r') as logfile:
            loglines = logfile.readlines()
        assert 1 == len(loglines)
        logmsg = loglines[0]
        assert "WARN" in logmsg and pipe_path in logmsg



class SampleSubtypeTests:
    """ ProtocolInterface attempts import of pipeline-specific Sample. """

    # Basic cases
    # 1 -- unmapped pipeline
    # 2 -- subtypes section is single string
    # 3 -- subtypes section is mapping ()
    # 4 -- subtypes section is missing (use single Sample subclass if there is one, base Sample for 0 or > 1 Sample subtypes defined)
    # 5 -- subtypes section is null  --> ALWAYS USE BASE SAMPLE (backdoor user side mechanism for making this be so)

    # Import trouble cases
    # No __main__
    # Argument parsing
    # missing import(s)

    # Subcases
    # 2 -- single string
    # 2a -- named class isn't defined in the module
    # 2b -- named class is in module but isn't defined
    #

    PROTOCOL_NAME_VARIANTS = [
            "ATAC-Seq", "ATACSeq", "ATACseq", "ATAC-seq", "ATAC",
            "ATACSEQ", "ATAC-SEQ", "atac", "atacseq", "atac-seq"]


    @pytest.mark.parametrize(
            argnames="pipe_key",
            argvalues=["{}.py".format(proto) for proto
                       in PROTOCOL_NAME_VARIANTS])
    @pytest.mark.parametrize(
            argnames="protocol",
            argvalues=PROTOCOL_NAME_VARIANTS)
    def test_pipeline_key_match_is_strict(
            self, tmpdir, pipe_key, protocol, atac_pipe_name,
            atacseq_iface_with_resources):
        """ Request for Sample subtype for unmapped pipeline is KeyError. """

        # Create the ProtocolInterface.
        strict_pipe_key = atac_pipe_name
        protocol_mapping = {protocol: strict_pipe_key}
        confpath = _write_config_data(
                protomap=protocol_mapping, dirpath=tmpdir.strpath,
                conf_data={strict_pipe_key: atacseq_iface_with_resources})
        piface = ProtocolInterface(confpath)

        # The absolute pipeline path is the pipeline name, joined to the
        # ProtocolInterface's pipelines location. This location is the
        # location from which a Sample subtype import is attempted.
        full_pipe_path = os.path.join(tmpdir.strpath, atac_pipe_name)

        # TODO: update to pytest.raises(None) if/when 3.1 adoption.
        # Match between pipeline key specified and the strict key used in
        # the mapping --> no error while mismatch --> error.
        if pipe_key == atac_pipe_name:
            piface.fetch_sample_subtype(
                protocol, pipe_key, full_pipe_path=full_pipe_path)
        else:
            with pytest.raises(KeyError):
                piface.fetch_sample_subtype(
                        protocol, pipe_key, full_pipe_path=full_pipe_path)


    @pytest.mark.parametrize(
            argnames=["mapped_protocol", "requested_protocol"],
            argvalues=itertools.combinations(PROTOCOL_NAME_VARIANTS, 2))
    def test_protocol_match_is_fuzzy(
            self, tmpdir, mapped_protocol, atac_pipe_name,
            requested_protocol, atacseq_piface_data):
        """ Punctuation and case mismatches are tolerated in protocol name. """

        # Needed to create the ProtocolInterface.
        protomap = {mapped_protocol: atac_pipe_name}
        # Needed to invoke the function under test.
        full_pipe_path = os.path.join(tmpdir.strpath, atac_pipe_name)

        # PipelineInterface data provided maps name to actual interface data
        # Mapping, so modify the ATAC-Seq mapping within that.
        # In this test, we're interested in the resolution of the protocol
        # name, that with it we can grab the name of a class. Thus, we
        # need only an arbitrary class name about which we can make the
        # relevant assertion(s).
        test_class_name = "TotallyArbitrary"
        atacseq_piface_data[atac_pipe_name]["sample_subtypes"] = \
                test_class_name

        # Write out configuration data and create the ProtocolInterface.
        conf_path = _write_config_data(
                protomap=protomap, conf_data=atacseq_piface_data,
                dirpath=tmpdir.strpath)
        piface = ProtocolInterface(conf_path)

        # Make the call under test, patching the function protected
        # function that's called iff the protocol name match succeeds.
        with mock.patch("looper.models._import_sample_subtype",
                        return_value=None) as mocked_import:
            # Return value is irrelevant; the effect of the protocol name
            # match/resolution is entirely observable via the argument to the
            # protected import function.
            piface.fetch_sample_subtype(
                    protocol=requested_protocol,
                    strict_pipe_key=atac_pipe_name,
                    full_pipe_path=full_pipe_path)
        # When the protocol name match/resolution succeeds, the name of the
        # Sample subtype class to which it was mapped is passed as an
        # argument to the protected import function.
        mocked_import.assert_called_with(full_pipe_path, test_class_name)



    @pytest.mark.parametrize(
            argnames="error_type",
            argvalues=CUSTOM_EXCEPTIONS +
                      BUILTIN_EXCEPTIONS_WITHOUT_REQUIRED_ARGUMENTS)
    def test_problematic_import_builtin_exception(
            self, tmpdir, error_type, atac_pipe_name, atacseq_piface_data):
        """ Base Sample is used if builtin exception on pipeline import. """

        # Values needed for object creation and function invocation
        protocol = ATAC_PROTOCOL_NAME
        protocol_mapping = {protocol: atac_pipe_name}
        full_pipe_path = os.path.join(tmpdir.strpath, atac_pipe_name)

        # Modify the data for the ProtocolInterface and create it.
        atacseq_piface_data[atac_pipe_name]["sample_subtypes"] = \
                {protocol: "IrrelevantClassname"}
        conf_path = _write_config_data(
                protomap=protocol_mapping,
                conf_data=atacseq_piface_data, dirpath=tmpdir.strpath)
        piface = ProtocolInterface(conf_path)

        # We want to test the effect of an encounter with an exception during
        # the import attempt, so patch the relevant function with a function
        # to raise the parameterized exception type.
        with mock.patch(
                "looper.utils.import_from_source",
                side_effect=error_type()):
            subtype = piface.fetch_sample_subtype(
                    protocol=protocol, strict_pipe_key=atac_pipe_name,
                    full_pipe_path=full_pipe_path)
        # When the import hits an exception, the base Sample type is used.
        assert subtype is Sample


    @pytest.mark.parametrize(
            argnames="num_sample_subclasses", argvalues=[0, 1, 2],
            ids=lambda n_samples:
            " num_sample_subclasses = {} ".format(n_samples))
    @pytest.mark.parametrize(
            argnames="decoy_class", argvalues=[False, True],
            ids=lambda decoy: " decoy_class = {} ".format(decoy))
    def test_no_subtypes_section(
            self, tmpdir, path_config_file, atac_pipe_name,
            num_sample_subclasses, decoy_class):
        """ DEPENDS ON PIPELINE MODULE CONTENT """

        # Basic values to invoke the function under test
        pipe_path = os.path.join(tmpdir.strpath, atac_pipe_name)
        piface = ProtocolInterface(path_config_file)

        # How to define the Sample subtypes (and non-subtype)
        sample_subclass_basename = "SampleSubclass"
        sample_lines = [
                "class {basename}{index}(Sample):",
                "\tdef __init__(*args, **kwargs):",
                "\t\tsuper({basename}{index}, self).__init__(*args, **kwargs)"]
        non_sample_class_lines = [
                "class NonSample(object):", "\tdef __init__(self):",
                "\t\tsuper(NonSample, self).__init__()"]

        # We expect the subtype iff there's just one Sample subtype.
        if num_sample_subclasses == 1:
            exp_subtype_name = "{}0".format(sample_subclass_basename)
        else:
            exp_subtype_name = Sample.__name__

        # Fill in the class definition template lines.
        def populate_sample_lines(n_classes):
            return [[sample_lines[0].format(basename=sample_subclass_basename,
                                            index=class_index),
                     sample_lines[1],
                     sample_lines[2].format(basename=sample_subclass_basename,
                                            index=class_index)]
                    for class_index in range(n_classes)]

        # Determine the groups of lines to permute.
        class_lines_pool = populate_sample_lines(num_sample_subclasses)
        if decoy_class:
            class_lines_pool.append(non_sample_class_lines)

        # Subtype fetch is independent of class declaration order,
        # so validate each permutation.
        for lines_order in itertools.permutations(class_lines_pool):
            # Write out class declarations and invoke the function under test.
            _create_module(lines_by_class=lines_order, filepath=pipe_path)
            subtype = piface.fetch_sample_subtype(
                    protocol=ATAC_PROTOCOL_NAME,
                    strict_pipe_key=atac_pipe_name, full_pipe_path=pipe_path)

            # Make the assertion on subtype name, getting additional
            # information about the module that we defined if there's failure.
            try:
                assert exp_subtype_name == subtype.__name__
            except AssertionError:
                with open(pipe_path, 'r') as f:
                    print("PIPELINE MODULE LINES: {}".
                          format("".join(f.readlines())))
                raise


    @pytest.mark.parametrize(
            argnames="subtype_name", argvalues=[Sample.__name__])
    def test_Sample_as_name(
            self, tmpdir, subtype_name, atac_pipe_name,
            atacseq_piface_data_with_subtypes):
        """ A pipeline may redeclare Sample as a subtype name. """

        # General values for the test
        subtype_name = Sample.__name__
        pipe_path = os.path.join(tmpdir.strpath, atac_pipe_name)

        # Define the subtype in the pipeline module.
        lines = ["from looper.models import Sample\n",
                 "class {}({}):\n".format(subtype_name, subtype_name),
                 "\tdef __init__(self, *args, **kwargs):\n",
                 "\t\tsuper({}, self).__init__(*args, **kwargs)\n".
                        format(subtype_name)]
        with open(pipe_path, 'w') as pipe_module_file:
            for l in lines:
                pipe_module_file.write(l)

        conf_path = _write_config_data(
                protomap={ATAC_PROTOCOL_NAME: atac_pipe_name},
                conf_data=atacseq_piface_data_with_subtypes,
                dirpath=tmpdir.strpath)
        piface = ProtocolInterface(conf_path)
        subtype = piface.fetch_sample_subtype(
                protocol=ATAC_PROTOCOL_NAME,
                strict_pipe_key=atac_pipe_name, full_pipe_path=pipe_path)

        # Establish that subclass relationship is improper.
        assert issubclass(Sample, Sample)
        # Our subtype derives from base Sample...
        assert issubclass(subtype, Sample)
        # ...but not vice-versa.
        assert not issubclass(Sample, subtype)
        # And we retained the name.
        assert subtype.__name__ == Sample.__name__


    @pytest.mark.parametrize(
            argnames="include_decoy", argvalues=[False, True])
    @pytest.mark.parametrize(argnames="subtype_name", argvalues=["NonSample"])
    @pytest.mark.parametrize(
            argnames="test_type",
            argvalues=["return_sample", "class_found"])
    def test_subtypes_non_implemented(
            self, tmpdir, atac_pipe_name,
            subtype_name, test_type, include_decoy,
            atacseq_piface_data_with_subtypes, subtypes_section_spec_type):
        """ Subtype in interface but not in pipeline is exceptional. """

        pipe_path = os.path.join(tmpdir.strpath, atac_pipe_name)

        # Write out the pipeline module file.
        if include_decoy:
            lines = ["class {}(object):\n".format(subtype_name),
                     "\tdef __init__(self, *args, **kwarggs):\n",
                     "\t\tsuper({}, self).__init__(*args, **kwargs)".
                            format(subtype_name)]
        else:
            lines = []
        with open(pipe_path, 'w') as pipe_module_file:
            for l in lines:
                pipe_module_file.write(l)

        # Create the ProtocolInterface.
        path_config_file = _write_config_data(
                protomap={ATAC_PROTOCOL_NAME: atac_pipe_name},
                conf_data=atacseq_piface_data_with_subtypes,
                dirpath=tmpdir.strpath)
        piface = ProtocolInterface(path_config_file)

        # Perform the call under test.
        kwargs = {"protocol": ATAC_PROTOCOL_NAME,
                  "strict_pipe_key": atac_pipe_name,
                  "full_pipe_path": pipe_path}
        if test_type not in ["return_sample", "class_found"]:
            raise ValueError("Unexpected test type: {}".format(test_type))
        if test_type == "return_sample":
            # We should always get back the base Sample...
            subtype = piface.fetch_sample_subtype(**kwargs)
            assert subtype is Sample
        else:
            with mock.patch("looper.models._proper_subtypes") as mocked_filter:
                piface.fetch_sample_subtype(**kwargs)
            # but have found the decoy class only if present.
            exp_cls_names = [subtype_name] if include_decoy else []
            positional_arguments = mocked_filter.call_args[0]
            types_found = positional_arguments[0]
            obs_cls_names = [t.__name__ for t in types_found]
            assert exp_cls_names == obs_cls_names


    def test_subtype_is_not_Sample(self):
        """ Subtype that doesn't extend Sample isn't used. """
        pass


    def test_subtypes_mapping_to_non_implemented_class(self):
        pass


    def test_subtypes_mapping_to_non_sample_subtype(self):
        pass


    def test_subtypes_section_is_sample_subtype(self):
        # Parameterize over mapping and singleton
        pass


    def test_sample_grandchild(self):
        """ The subtype to be used can be a grandchild of Sample. """
        # Can parameterize but don't need to
        pass


    def test_has_subtypes_mapping_but_protocol_doesnt_match(self):
        # Intrinsic to mapping; this is a failure case.
        pass


    @pytest.fixture(scope="function")
    def atacseq_piface_data_with_subtypes(
            self, request, atacseq_piface_data, atac_pipe_name):
        """
        Provide test case with ProtocolInterface data.

        :param pytest._pytest.fixtures.SubRequest request: test case
            requesting the parameterization
        :param Mapping atacseq_piface_data: the ProtocolInterface data
        :param str atac_pipe_name: name for the pipeline
        :return Mapping: same as input, but with Sample subtype specification
            section mixed in
        """

        # Get the test case's parameterized values.
        spec_type = request.getfixturevalue("subtypes_section_spec_type")
        subtype_name = request.getfixturevalue("subtype_name")

        # Determine how to specify the subtype(s).
        if spec_type is str:
            section_value = subtype_name
        elif spec_type is dict:
            section_value = {ATAC_PROTOCOL_NAME: subtype_name}
        else:
            raise ValueError("Unexpected subtype section specification type: "
                             "{}".format(spec_type))

        # Update and return the interface data.
        atacseq_piface_data[atac_pipe_name]["sample_subtypes"] = section_value
        return atacseq_piface_data



def _create_module(lines_by_class, filepath):
    """
    Write out lines that will defined a module.

    :param Sequence[str] lines_by_class: lines that define a class
    :param str filepath: path to module file to create
    :return str: path to the module file written
    """
    header = "from looper.models import Sample"
    lines = "\n\n".join(
        [header] + ["\n".join(class_lines)
                    for class_lines in lines_by_class])
    with open(filepath, 'w') as modfile:
        modfile.write("{}\n".format(lines))
    return filepath



def _write_config_data(protomap, conf_data, dirpath):
    """
    Write ProtocolInterface data to (temp)file.

    :param Mapping protomap: mapping from protocol name to pipeline key/name
    :param Mapping conf_data: mapping from pipeline key/name to configuration
        data for a PipelineInterface
    :param str dirpath: path to filesystem location in which to place the
        file to write
    :return str: path to the (temp)file written
    """
    full_conf_data = {"protocol_mapping": protomap, "pipelines": conf_data}
    filepath = os.path.join(dirpath, "pipeline_interface.yaml")
    with open(filepath, 'w') as conf_file:
        yaml.safe_dump(full_conf_data, conf_file)
    return filepath
