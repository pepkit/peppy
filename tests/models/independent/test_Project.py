""" Tests for the NGS Project model. """

import copy
import os
import mock
import pytest
import yaml
from looper.models import \
        Project, MissingMetadataException, SAMPLE_ANNOTATIONS_KEY


__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"



@pytest.fixture(scope="function")
def project_config_data():
    return {
        "metadata": {
            SAMPLE_ANNOTATIONS_KEY: "sample-anns-filler.csv",
            "output_dir": "$HOME/sequencing/output",
            "pipelines_dir": "${CODE}/pipelines"},
        "data_sources": {"arbitrary": "placeholder/data/{filename}"},
        "genomes": {"human": "hg19", "mouse": "mm10"},
        "transcriptomes": {"human": "hg19_cdna", "mouse": "mm10_cdna"}}



def pytest_generate_tests(metafunc):
    """ Dynamic parameterization/customization for tests in this module. """
    if metafunc.cls == DerivedColumnsTests:
        # Parameterize derived columns tests over whether the specification
        # is explicit (vs. implied), and which default column to validate.
        metafunc.parametrize(
                argnames="case_type",
                argvalues=DerivedColumnsTests.DERIVED_COLUMNS_CASE_TYPES,
                ids=lambda case_type: "case_type={}".format(case_type))



class ProjectRequirementsTests:
    """ Tests for a Project's set of requirements. """


    def test_lacks_sample_annotations(
            self, project_config_data, env_config_filepath, tmpdir):
        """ Lack of sample annotations precludes Project construction. """

        # Remove sample annotations KV pair from config data for this test.
        del project_config_data["metadata"][SAMPLE_ANNOTATIONS_KEY]

        # Write the config and assert the expected exception for Project ctor.
        conf_path = _write_project_config(
            project_config_data, dirpath=tmpdir.strpath)
        with pytest.raises(MissingMetadataException):
            Project(conf_path, default_compute=env_config_filepath)


    def test_minimal_configuration_doesnt_fail(
            self, minimal_project_conf_path, env_config_filepath):
        """ Project ctor requires minimal config and default environment. """
        Project(config_file=minimal_project_conf_path,
                default_compute=env_config_filepath)


    def test_minimal_configuration_name_inference(
            self, tmpdir, minimal_project_conf_path, env_config_filepath):
        """ Project infers name from where its configuration lives. """
        project = Project(minimal_project_conf_path,
                          default_compute=env_config_filepath)
        _, expected_name = os.path.split(tmpdir.strpath)
        assert expected_name == project.name


    def test_minimal_configuration_output_dir(
            self, tmpdir, minimal_project_conf_path, env_config_filepath):
        """ Project infers output path from its configuration location. """
        project = Project(minimal_project_conf_path,
                          default_compute=env_config_filepath)
        assert tmpdir.strpath == project.output_dir



class DerivedColumnsTests:
    """ Tests for the behavior of Project's derived_columns attribute. """

    ADDITIONAL_DERIVED_COLUMNS = ["arbitrary1", "filler2", "placeholder3"]
    DERIVED_COLUMNS_CASE_TYPES = ["implicit", "disjoint", "intersection"]


    def create_project(
            self, project_config_data, default_env_path, case_type, dirpath):
        """
        For a test case, determine expectations and create Project instance.
        
        :param dict project_config_data: the actual data to write to the 
            Project configuration file
        :param str default_env_path: path to the default environment config 
            file to pass to Project constructor
        :param str case_type: type of test case to execute; this determines 
            how to specify the derived columns in the config file
        :param str dirpath: path in which to write config file
        :return (Iterable[str], Project): collection of names of derived 
            columns to expect, along with Project instance with which to test
        """

        # Ensure valid parameterization.
        if case_type not in self.DERIVED_COLUMNS_CASE_TYPES:
            raise ValueError(
                "Unexpected derived_columns case type: '{}' (known={})".
                format(case_type, self.DERIVED_COLUMNS_CASE_TYPES))

        # Parameterization specifies expectation and explicit specification.
        expected_derived_columns = copy.copy(Project.DERIVED_COLUMNS_DEFAULT)
        if case_type == "implicit":
            # Negative control; ensure config data lacks derived columns.
            assert "derived_columns" not in project_config_data
        else:
            explicit_derived_columns = \
                    copy.copy(self.ADDITIONAL_DERIVED_COLUMNS)
            expected_derived_columns.extend(self.ADDITIONAL_DERIVED_COLUMNS)
            # Determine explicit inclusion of default derived columns.
            if case_type == "intersection":
                explicit_derived_columns.extend(
                        Project.DERIVED_COLUMNS_DEFAULT)
            project_config_data["derived_columns"] = explicit_derived_columns

        # Write the config and build the Project.
        conf_file_path = _write_project_config(
                project_config_data, dirpath=dirpath)
        with mock.patch("looper.models.Project.add_sample_sheet"):
            project = Project(conf_file_path, default_compute=default_env_path)
        return expected_derived_columns, project



    def test_default_derived_columns_always_present(self,
            env_config_filepath, project_config_data, case_type, tmpdir):
        """ Explicit or implicit, default derived columns are always there. """

        expected_derived_columns, project = self.create_project(
                project_config_data=project_config_data,
                default_env_path=env_config_filepath,
                case_type=case_type, dirpath=tmpdir.strpath)

        # Rough approximation of order-agnostic validation of
        # presence and number agreement for all elements.
        assert len(expected_derived_columns) == len(project.derived_columns)
        assert set(expected_derived_columns) == set(project.derived_columns)


    def test_default_derived_columns_not_duplicated(self,
            env_config_filepath, project_config_data, case_type, tmpdir):
        """ Default derived columns are not added if already present. """
        from collections import Counter
        _, project = self.create_project(
                project_config_data=project_config_data,
                default_env_path=env_config_filepath,
                case_type=case_type, dirpath=tmpdir.strpath)
        num_occ_by_derived_column = Counter(project.derived_columns)
        for default_derived_colname in Project.DERIVED_COLUMNS_DEFAULT:
            assert 1 == num_occ_by_derived_column[default_derived_colname]



class ProjectPipelineArgstringTests:
    """ Tests for Project config's pipeline_arguments section. """

    # Data to add to project config based on test case parameterization
    PIPELINE_ARGS_FLAGS_ONLY = {
        "ATACSeq.py": {"-D": None},
        "rrbs.py": {"--epilog": None, "--use-strand": None}
    }
    PIPELINE_ARGS_OPTIONS_ONLY = {
        "ATACSeq.py": {"--frip-peaks": "/atac/metadata/CD4_hotSpot.bed"},
        "rrbs.py": {"--rrbs-fill": "4", "--quality-threshold": "30"}
    }
    # Combine the flags- and options-only argument maps.
    PIPELINE_ARGS_MIXED = copy.deepcopy(PIPELINE_ARGS_FLAGS_ONLY)
    for pipeline, args_data in PIPELINE_ARGS_OPTIONS_ONLY.items():
        PIPELINE_ARGS_MIXED[pipeline].update(**args_data)
    
    # Map heterogeneity keyword argument for test parameterization 
    # to project config data and expected argstring components.
    DATA_BY_CASE_TYPE = {
        "flags": PIPELINE_ARGS_FLAGS_ONLY, 
        "options": PIPELINE_ARGS_OPTIONS_ONLY, 
        "mixed": PIPELINE_ARGS_MIXED}
    EXPECTATIONS_BY_CASE_TYPE = {
        # Just the flags themselves are components.
        "flags": {pipe: set(flags_encoding.keys())
                  for pipe, flags_encoding
                  in PIPELINE_ARGS_FLAGS_ONLY.items()},
        # Pair option with argument for non-flag command components.
        "options": {pipe: set(opts_encoding.items())
                    for pipe, opts_encoding
                    in PIPELINE_ARGS_OPTIONS_ONLY.items()},
        # Null-valued KV pairs represent flags, not options.
        "mixed": {pipe: {opt if arg is None else (opt, arg)
                         for opt, arg in mixed_encoding.items()}
                  for pipe, mixed_encoding in PIPELINE_ARGS_MIXED.items()}}


    @pytest.mark.parametrize(argnames="pipeline",
                             argvalues=["arb-pipe-1", "dummy_pipeline_2"])
    def test_no_pipeline_args(self, tmpdir, pipeline,
                              env_config_filepath, project_config_data):
        """ Project need not specify pipeline arguments. """
        # Project-level argstring is empty if pipeline_args section is absent.
        assert [""] == self.observed_argstring_elements(
                project_config_data, pipeline, 
                confpath=tmpdir.strpath, envpath=env_config_filepath)


    @pytest.mark.parametrize(
            argnames="pipeline", argvalues=["not-mapped-1", "unmapped_2"])
    @pytest.mark.parametrize(
            argnames="pipeline_args",
            argvalues=[PIPELINE_ARGS_FLAGS_ONLY,
                       PIPELINE_ARGS_OPTIONS_ONLY, PIPELINE_ARGS_MIXED],
            ids=lambda pipe_args: "pipeline_args: {}".format(pipe_args))
    def test_pipeline_args_different_pipeline(
            self, tmpdir, pipeline, pipeline_args,
            env_config_filepath, project_config_data):
        """ Project-level argstring is empty for unmapped pipeline name. """
        # Project-level argstring is empty if pipeline_args section is absent.
        project_config_data["pipeline_args"] = pipeline_args
        observed_argstring_elements = self.observed_argstring_elements(
                project_config_data, pipeline, 
                confpath=tmpdir.strpath, envpath=env_config_filepath)
        assert [""] == observed_argstring_elements


    @pytest.mark.parametrize(
            argnames="pipeline", argvalues=PIPELINE_ARGS_MIXED.keys())
    @pytest.mark.parametrize(
            argnames="optargs", argvalues=EXPECTATIONS_BY_CASE_TYPE.keys())
    def test_pipeline_args_pipeline_match(
            self, pipeline, optargs, tmpdir, 
            project_config_data, env_config_filepath):
        """ Project does flags-only, options-only, or mixed pipeline_args. """

        # Allow parameterization to determine pipeline_args section content.
        project_config_data["pipeline_args"] = self.DATA_BY_CASE_TYPE[optargs]

        # Expectation arises from section content and requested pipeline.
        expected_argstring_components = \
                self.EXPECTATIONS_BY_CASE_TYPE[optargs][pipeline]

        # Write config, make Project, and request argstring.
        observed_argstring_elements = self.observed_argstring_elements(
                project_config_data, pipeline,
                confpath=tmpdir.strpath, envpath=env_config_filepath)

        # Format the flags/opt-arg pairs for validation.
        observed_argstring_elements = self._parse_flags_and_options(
                observed_argstring_elements)

        assert expected_argstring_components == observed_argstring_elements


    @pytest.mark.parametrize(
            argnames="default", 
            argvalues=[{"-D": None},
                       {"--verbosity": "1", "-D": None, "--dirty": None}])
    @pytest.mark.parametrize(
            argnames="pipeline", 
            argvalues=["missing1", "arbitrary2"] + 
                      list(PIPELINE_ARGS_MIXED.keys()))
    def test_default_only(
            self, default, pipeline, tmpdir, 
            project_config_data, env_config_filepath):
        """ Project always adds any default pipeline arguments. """
        project_config_data["pipeline_args"] = {"default": default}
        expected_components = {opt if arg is None else (opt, arg)
                               for opt, arg in default.items()}
        observed_argstring_elements = self.observed_argstring_elements(
                project_config_data, pipeline, 
                confpath=tmpdir.strpath, envpath=env_config_filepath)
        observed_argstring_elements = \
                self._parse_flags_and_options(observed_argstring_elements)
        assert expected_components == observed_argstring_elements


    @pytest.mark.parametrize(
            argnames="default", 
            argvalues=[{"-D": None},
                       {"--verbosity": "1", "-D": None, "--dirty": None}])
    @pytest.mark.parametrize(
            argnames="pipeline", argvalues=PIPELINE_ARGS_MIXED.keys())
    def test_default_plus_non_default(
            self, default, pipeline, tmpdir,
            project_config_data, env_config_filepath):
        """ Default arguments apply to all pipelines; others are specific. """
        case_type = "mixed"
        pipeline_args = copy.deepcopy(self.DATA_BY_CASE_TYPE[case_type])
        pipeline_args["default"] = default
        project_config_data["pipeline_args"] = pipeline_args
        observed_components = self.observed_argstring_elements(
                project_config_data, pipeline,
                confpath=tmpdir.strpath, envpath=env_config_filepath)
        observed_components = \
                self._parse_flags_and_options(observed_components)
        expected_from_default = \
                {opt if arg is None else (opt, arg)
                 for opt, arg in default.items()}
        expected_from_pipeline = \
                self.EXPECTATIONS_BY_CASE_TYPE[case_type][pipeline]
        expected_components = expected_from_default | expected_from_pipeline
        assert expected_components == observed_components


    def test_path_expansion(
            self, tmpdir, project_config_data, env_config_filepath):
        """ Path values in pipeline_args expand environment variables. """
        pipeline = "wgbs.py"
        genomes_extension = "mm10/indexed_epilog/mm10_cg.tsv.gz"
        genomes_substitution = os.path.expandvars("$HOME")
        pipeline_args = {pipeline: {
                "--positions": "$HOME/{}".format(genomes_extension)}}
        project_config_data["pipeline_args"] = pipeline_args
        expected = "--positions {}/{}".format(genomes_substitution, 
                                              genomes_extension)
        observed = self.observed_argstring_elements(
                project_config_data, pipeline, 
                confpath=tmpdir.strpath, envpath=env_config_filepath)
        assert expected.split(" ") == observed


    def observed_argstring_elements(
            self, confdata, pipeline, confpath, envpath):
        """
        Write config, build project, and validate argstring for pipeline.
        
        :param dict confdata: project configuration data
        :param str pipeline: name of pipeline for which to build argstring
        :param str confpath: where to write project config file
        :param str envpath: pointer to default environment file
        :return Iterable[str] argstring components
        """
        conf_file_path = _write_project_config(confdata, dirpath=confpath)

        # Subvert requirement for sample annotations file.
        with mock.patch("looper.models.Project.add_sample_sheet"):
            project = Project(conf_file_path, default_compute=envpath)

        argstring = project.get_arg_string(pipeline)
        return argstring.split(" ")
    
    
    @staticmethod
    def _parse_flags_and_options(command_elements):
        """
        Differentiate flags and option/argument pairs for validation.
        
        We need a way to assert that each option is adjacent to and precedes 
        its argument. This creates some difficulty since we want to be 
        disregard order of the flags/option-argument pairs with respect to one 
        another when we validate. The desire to validate a mixture of flags 
        and option/argument pairs precludes some indexing-based approaches to 
        the problem. Two strategies are most apparent, each with a minor 
        pitfall. We can regard any command element starting with a hyphen as 
        a flag or an option, and all others as arguments, but this excludes 
        the possibility of negative integers as arguments. Or we could assume 
        that each element with a double-hyphen prefix takes and argument, but 
        this seems even less reasonable. Let's settle on the first strategy.

        :param Iterable[str] command_elements: components of a command
        :return Iterable[str | (str, str)]: collection of flags or pairs 
            of option and argument
        """
        # Determine which positions appear to hold an argument
        # rather than a flag or an option name.
        is_arg = [not cmd_elem.startswith("-")
                  for cmd_elem in command_elements]

        parsed_command_elements = set()

        # Step through the command elements, using knowledge of argument index.
        for i, cmd_elem in enumerate(command_elements):
            if is_arg[i]:
                # This position's been added as an argument.
                continue
            try:
                # Could be in final position
                if is_arg[i + 1]:
                    # Pair option with argument.
                    parsed_command_elements.add(
                            (cmd_elem, command_elements[i + 1]))
                else:
                    # Add the flag.
                    parsed_command_elements.add(cmd_elem)
            except IndexError:
                # Add the final element.
                parsed_command_elements.add(cmd_elem)

        return parsed_command_elements


def _write_project_config(config_data, dirpath, filename="proj-conf.yaml"):
    """
    Write the configuration file for a Project.
    
    :param dict config_data: configuration data to write to disk
    :param str dirpath: path to folder in which to place file
    :param str filename: name for config file
    :return str: path to config file written
    """
    conf_file_path = os.path.join(dirpath, filename)
    with open(conf_file_path, 'w') as conf_file:
        yaml.safe_dump(config_data, conf_file)
    return conf_file_path
