""" Tests for the NGS Project model. """

import copy
import logging
import os

import mock
from numpy import random as nprand
import pytest
import yaml

import pep
from peppy import AttributeDict, Project, Sample
from peppy.const import SAMPLE_ANNOTATIONS_KEY, SAMPLE_NAME_COLNAME
from peppy.project import _MissingMetadataException
from peppy.sample import COL_KEY_SUFFIX
from tests.conftest import \
    DERIVED_COLNAMES, EXPECTED_MERGED_SAMPLE_FILES, \
    MERGED_SAMPLE_INDICES, NUM_SAMPLES
from tests.helpers import named_param


__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"



@pytest.fixture(scope="function")
def project_config_data():
    """ Provide some basic data for a Project configuration. """
    return {
        "metadata": {
            SAMPLE_ANNOTATIONS_KEY: "sample-anns-filler.csv",
            "output_dir": "$HOME/sequencing/output",
            "pipeline_interfaces": "${CODE}/pipelines"},
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



class ProjectConstructorTests:
    """ Tests of Project constructor, particularly behavioral details. """


    def test_no_samples(self, path_empty_project):
        """ Lack of Samples is unproblematic. """
        p = Project(path_empty_project)
        assert 0 == p.num_samples
        assert [] == list(p.samples)



    @pytest.mark.parametrize(
            argnames="spec_type", argvalues=["as_null", "missing"],
            ids=lambda spec: "spec_type={}".format(spec))
    @pytest.mark.parametrize(
            argnames="lazy", argvalues=[False, True],
            ids=lambda lazy: "lazy={}".format(lazy))
    def test_no_sample_subannotation_in_config(
            self, tmpdir, spec_type, lazy, proj_conf_data, path_sample_anns):
        """ Merge table attribute remains null if config lacks subannotation. """
        metadata = proj_conf_data["metadata"]
        try:
            assert "sample_subannotation" in metadata
        except AssertionError:
            print("Project metadata section lacks 'sample_subannotation'")
            print("All config data: {}".format(proj_conf_data))
            print("Config metadata section: {}".format(metadata))
            raise
        if spec_type == "as_null":
            metadata["sample_subannotation"] = None
        elif spec_type == "missing":
            del metadata["sample_subannotation"]
        else:
            raise ValueError("Unknown way to specify no merge table: {}".
                             format(spec_type))
        path_config_file = os.path.join(tmpdir.strpath, "project_config.yaml")
        with open(path_config_file, 'w') as conf_file:
            yaml.safe_dump(proj_conf_data, conf_file)
        p = Project(path_config_file, defer_sample_construction=lazy)
        assert p.sample_subannotation is None


    @pytest.mark.skip("Not implemented")
    def test_sample_subannotation_construction(
            self, tmpdir, project_config_data):
        """ Merge table is constructed iff samples are constructed. """
        # TODO: implement
        pass


    def test_counting_samples_doesnt_create_samples(
            self, sample_annotation_lines,
            path_project_conf, path_sample_anns):
        """ User can ask about sample count without creating samples. """
        # We're not parameterized in terms of Sample creation laziness here
        # because a piece of the test's essence is Sample collection absence.
        p = Project(path_project_conf, defer_sample_construction=True)
        assert p._samples is None
        expected_sample_count = sum(1 for _ in sample_annotation_lines) - 1
        assert expected_sample_count == p.num_samples
        assert p._samples is None


    @pytest.mark.parametrize(argnames="lazy", argvalues=[False, True])
    def test_sample_creation_laziness(
            self, path_project_conf, path_sample_anns, lazy):
        """ Project offers control over whether to create base Sample(s). """

        p = Project(path_project_conf, defer_sample_construction=lazy)

        if lazy:
            # Samples should remain null during lazy Project construction.
            assert p._samples is None

        else:
            # Eager Project construction builds Sample objects.
            assert p._samples is not None
            with open(path_sample_anns, 'r') as anns_file:
                anns_file_lines = anns_file.readlines()

            # Sum excludes the header line.
            num_samples_expected = sum(1 for l in anns_file_lines[1:] if l)
            assert num_samples_expected == len(p._samples)
            assert all([Sample == type(s) for s in p._samples])


    @pytest.mark.parametrize(argnames="lazy", argvalues=[False, True])
    def test_sample_name_availability(
            self, path_project_conf, path_sample_anns, lazy):
        """ Sample names always available on Project. """
        with open(path_sample_anns, 'r') as anns_file:
            expected_sample_names = \
                    [l.split(",")[0] for l in anns_file.readlines()[1:] if l]
        p = Project(path_project_conf, defer_sample_construction=lazy)
        assert expected_sample_names == list(p.sample_names)



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
        with pytest.raises(_MissingMetadataException):
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



class ProjectDefaultEnvironmentSettingsTests:
    """ Project can use default environment settings but doesn't need them. """

    # Base/default environment data to write to disk
    ENVIRONMENT_CONFIG_DATA = {"compute": {
        "default": {
            "submission_template": "templates/slurm_template.sub",
            "submission_command": "sbatch",
            "partition": "serial"},
        "local": {
            "submission_template": "templates/localhost_template.sub",
            "submission_command": "sh"}
    }}


    @pytest.mark.parametrize(
            argnames="explicit_null", argvalues=[False, True],
            ids=lambda explicit_null: "explicit_null={}".format(explicit_null))
    @pytest.mark.parametrize(
            argnames="compute_env_attname",
            argvalues=["environment", "environment_file", "compute"],
            ids=lambda attr: "attr={}".format(attr))
    def test_no_default_env_settings_provided(
            self, minimal_project_conf_path,
            explicit_null, compute_env_attname):
        """ Project doesn't require default environment settings. """

        kwargs = {"default_compute": None} if explicit_null else {}
        project = Project(minimal_project_conf_path, **kwargs)

        observed_attribute = getattr(project, compute_env_attname)
        expected_attribute = \
                self.default_compute_settings(project)[compute_env_attname]

        if compute_env_attname == "compute":
            # 'compute' refers to a section in the default environment
            # settings file and also to a Project attribute. A Project
            # instance selects just one of the options in the 'compute'
            # section of the file as the value for its 'compute' attribute.
            expected_attribute = expected_attribute["default"]
            observed_attribute = _compute_paths_to_names(observed_attribute)
        elif compute_env_attname == "environment":
            envs_with_reduced_filepaths = \
                    _env_paths_to_names(observed_attribute["compute"])
            observed_attribute = AttributeDict(
                    {"compute": envs_with_reduced_filepaths})

        assert expected_attribute == observed_attribute


    @pytest.mark.parametrize(
            argnames="envconf_filename",
            argvalues=["arbitrary-envconf.yaml",
                       "nonexistent_environment.yaml"])
    def test_nonexistent_env_settings_file(
            self, tmpdir, minimal_project_conf_path,
            env_config_filepath, envconf_filename):
        """ Project doesn't require default environment settings. """

        # Create name to nonexistent file based on true default file.
        envconf_dirpath, _ = os.path.split(env_config_filepath)
        misnamed_envconf = os.path.join(envconf_dirpath, envconf_filename)

        # Create and add log message handler for expected errors.
        logfile = tmpdir.join("project-error-messages.log").strpath
        expected_error_message_handler = logging.FileHandler(logfile, mode='w')
        expected_error_message_handler.setLevel(logging.ERROR)
        pep.project._LOGGER.handlers.append(expected_error_message_handler)

        # Create Project, expecting to generate error messages.
        project = Project(minimal_project_conf_path,
                          default_compute=misnamed_envconf)

        # Remove the temporary message handler.
        del pep.project._LOGGER.handlers[-1]

        # Ensure nulls for all relevant Project attributes.
        self._assert_null_compute_environment(project)
        # We should have two error messages, describing the exception caught
        # during default environment parsing and that it couldn't be set.
        with open(logfile, 'r') as messages:
            exception_messages = messages.readlines()
        try:
            assert 2 == len(exception_messages)
        except AssertionError:
            print("Exception messages: {}".format(exception_messages))
            raise


    def test_project_environment_uses_default_environment_settings(
            self, project, expected_environment):
        """ Project updates environment settings if given extant file. """
        assert expected_environment == project.environment


    def test_project_compute_uses_default_environment_settings(
            self, project, expected_environment):
        """ Project parses out 'default' environment settings as 'compute'. """
        assert project.compute == expected_environment["compute"]["default"]


    @pytest.fixture(scope="function")
    def project(self, tmpdir, minimal_project_conf_path):
        """ Create a Project with base/default environment. """
        # Write base/default environment data to disk.
        env_config_filename = "env-conf.yaml"
        env_config_filepath = tmpdir.join(env_config_filename).strpath
        with open(env_config_filepath, 'w') as env_conf:
            yaml.safe_dump(self.ENVIRONMENT_CONFIG_DATA, env_conf)
        return Project(minimal_project_conf_path,
                          default_compute=env_config_filepath)


    @pytest.fixture(scope="function")
    def expected_environment(self, tmpdir):
        """ Derive Project's expected base/default environment. """
        # Expand submission template paths in expected environment.
        expected_environment = copy.deepcopy(self.ENVIRONMENT_CONFIG_DATA)
        for envname, envdata in self.ENVIRONMENT_CONFIG_DATA[
            "compute"].items():
            base_submit_template = envdata["submission_template"]
            expected_environment["compute"][envname]["submission_template"] = \
                os.path.join(tmpdir.strpath, base_submit_template)
        return expected_environment


    @staticmethod
    def _assert_null_compute_environment(project):
        assert project.environment is None
        assert project.environment_file is None
        assert project.compute is None


    @staticmethod
    def default_compute_settings(project):
        settings_filepath = project.default_compute_envfile
        with open(settings_filepath, 'r') as settings_data_file:
            settings = yaml.safe_load(settings_data_file)
        return {"environment": copy.deepcopy(settings),
                "environment_file": settings_filepath,
                "compute": copy.deepcopy(settings)["compute"]}



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
        with mock.patch("pep.project.check_sample_sheet"):
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
        with mock.patch("pep.project.check_sample_sheet"):
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



@pytest.mark.usefixtures("write_project_files")
class ProjectConstructorTest:


    @pytest.mark.parametrize(argnames="attr_name",
                             argvalues=["required_inputs", "all_input_attr"])
    def test_sample_required_inputs_not_set(self, proj, attr_name):
        """ Samples' inputs are not set in `Project` ctor. """
        with pytest.raises(AttributeError):
            getattr(proj.samples[nprand.randint(len(proj.samples))], attr_name)


    @pytest.mark.parametrize(argnames="sample_index",
                             argvalues=MERGED_SAMPLE_INDICES)
    def test_merge_samples_positive(self, proj, sample_index):
        """ Samples annotation lines say only sample 'b' should be merged. """
        assert proj.samples[sample_index].merged


    @pytest.mark.parametrize(argnames="sample_index",
                             argvalues=set(range(NUM_SAMPLES)) -
                                       MERGED_SAMPLE_INDICES)
    def test_merge_samples_negative(self, proj, sample_index):
        assert not proj.samples[sample_index].merged


    @pytest.mark.parametrize(argnames="sample_index",
                             argvalues=MERGED_SAMPLE_INDICES)
    def test_data_sources_derivation(self, proj, sample_index):
        """ Samples in merge file, check data_sources --> derived_columns. """
        # Make sure these columns were merged:
        merged_columns = filter(
                lambda col_key: (col_key != "col_modifier") and
                                not col_key.endswith(COL_KEY_SUFFIX),
                proj.samples[sample_index].merged_cols.keys())
        # Order may be lost due to mapping.
        # We don't care about that here, or about duplicates.
        expected = set(DERIVED_COLNAMES)
        observed = set(merged_columns)
        assert expected == observed


    @named_param(argnames="sample_index", argvalues=MERGED_SAMPLE_INDICES)
    def test_derived_columns_sample_subannotation_sample(
            self, proj, sample_index):
        """ Make sure derived columns works on merged table. """
        observed_merged_sample_filepaths = \
            [os.path.basename(f) for f in
             proj.samples[sample_index].file2.split(" ")]
        assert EXPECTED_MERGED_SAMPLE_FILES == \
               observed_merged_sample_filepaths


    @named_param(argnames="sample_index",
                 argvalues=set(range(NUM_SAMPLES)) - MERGED_SAMPLE_INDICES)
    def test_unmerged_samples_lack_merged_cols(self, proj, sample_index):
        """ Samples not in the `sample_subannotation` lack merged columns. """
        # Assert the negative to cover empty dict/AttributeDict/None/etc.
        assert not proj.samples[sample_index].merged_cols


    def test_duplicate_derived_columns_still_derived(self, proj):
        """ Duplicated derived columns can still be derived. """
        sample_index = 2
        observed_nonmerged_col_basename = \
            os.path.basename(proj.samples[sample_index].nonmerged_col)
        assert "c.txt" == observed_nonmerged_col_basename
        assert "" == proj.samples[sample_index].locate_data_source(
                proj.data_sources, 'file')



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



def _env_paths_to_names(envs):
    """
    Convert filepath(s) in each environment to filename for assertion.

    Project instance will ensure that filepaths are absolute, but we want
    assertion logic here to be independent of that (unless that's under test).

    :param Mapping[str, Mapping]: environment data by name
    :return Mapping[str, Mapping]: same as the input,
        but with conversion(s) performed
    """
    reduced = {}
    for env_name, env_data in envs.items():
        reduced[env_name] = _compute_paths_to_names(env_data)
    return reduced



def _compute_paths_to_names(env):
    """
    Single-environment version of conversion of filepath(s) to name(s).

    This is similarly motivated by allowing tests' assertions about
    equality between Mappings to be independent of Project instance's
    effort to ensure that filepaths are absolute.

    :param Mapping env: environment datum by name
    :return Mapping: same as the input, but with conversion(s) performed
    """
    reduced = copy.deepcopy(env)
    for pathvar in ["submission_template"]:
        _, reduced[pathvar] = os.path.split(reduced[pathvar])
    return reduced
