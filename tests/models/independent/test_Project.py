""" Tests for the NGS Project model. """

import copy
import os
import warnings

import mock
from numpy import random as nprand
import pytest
import yaml

from peppy import Project, Sample
from peppy.const import *
from peppy.project import GENOMES_KEY, NEW_PIPES_KEY, TRANSCRIPTOMES_KEY, \
    MissingSubprojectError
from peppy.sample import COL_KEY_SUFFIX
from tests.conftest import \
    DERIVED_COLNAMES, EXPECTED_MERGED_SAMPLE_FILES, \
    MERGED_SAMPLE_INDICES, NUM_SAMPLES
from tests.helpers import named_param


__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"


_GENOMES = {"human": "hg19", "mouse": "mm10"}
_TRANSCRIPTOMES = {"human": "hg19_cdna", "mouse": "mm10_cdna"}


@pytest.fixture(scope="function")
def project_config_data():
    """ Provide some basic data for a Project configuration. """
    return {
        METADATA_KEY: {
            NAME_TABLE_ATTR: "samples.csv",
            OUTDIR_KEY: "$HOME/sequencing/output",
            NEW_PIPES_KEY: "${CODE}/pipelines"},
        DATA_SOURCES_SECTION: {"arbitrary": "placeholder/data/{filename}"},
    }


def pytest_generate_tests(metafunc):
    """ Dynamic parameterization/customization for tests in this module. """
    if metafunc.cls == DerivedAttributesTests:
        # Parameterize derived attribute tests over whether the specification
        # is explicit (vs. implied), and which default attribute to validate.
        metafunc.parametrize(
                argnames="case_type",
                argvalues=DerivedAttributesTests.DERIVED_ATTRIBUTES_CASE_TYPES,
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
        """ Subannotation attribute remains null if config lacks subannotation. """
        metadata = proj_conf_data[METADATA_KEY]
        try:
            assert SAMPLE_SUBANNOTATIONS_KEY in metadata
        except AssertionError:
            print("Project metadata section lacks '{}'".format(SAMPLE_SUBANNOTATIONS_KEY))
            print("All config data: {}".format(proj_conf_data))
            print("Config metadata section: {}".format(metadata))
            raise
        if spec_type == "as_null":
            metadata[SAMPLE_SUBANNOTATIONS_KEY] = None
        elif spec_type == "missing":
            del metadata[SAMPLE_SUBANNOTATIONS_KEY]
        else:
            raise ValueError("Unknown way to specify no merge table: {}".
                             format(spec_type))
        path_config_file = os.path.join(tmpdir.strpath, "project_config.yaml")
        with open(path_config_file, 'w') as conf_file:
            yaml.safe_dump(proj_conf_data, conf_file)
        p = Project(path_config_file, defer_sample_construction=lazy)
        assert getattr(p, SAMPLE_SUBANNOTATIONS_KEY) is None

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

    def test_lacks_sample_annotation(
            self, project_config_data, env_config_filepath, tmpdir):
        """ Project can be built without sample annotations. """
        # Remove sample annotations KV pair from config data for this test.
        del project_config_data[METADATA_KEY][NAME_TABLE_ATTR]
        # Write the (sans-annotations) config and assert Project is created.
        conf_path = _write_project_config(
            project_config_data, dirpath=tmpdir.strpath)
        prj = Project(conf_path)
        assert isinstance(prj, Project)

    def test_minimal_configuration_doesnt_fail(
            self, minimal_project_conf_path, env_config_filepath):
        """ Project ctor requires minimal config and default environment. """
        Project(config_file=minimal_project_conf_path)

    def test_minimal_configuration_name_inference(
            self, tmpdir, minimal_project_conf_path, env_config_filepath):
        """ Project infers name from where its configuration lives. """
        project = Project(minimal_project_conf_path)
        _, expected_name = os.path.split(tmpdir.strpath)
        assert expected_name == project.name

    def test_minimal_configuration_output_dir(
            self, tmpdir, minimal_project_conf_path, env_config_filepath):
        """ Project infers output path from its configuration location. """
        project = Project(minimal_project_conf_path)
        assert tmpdir.strpath == project.output_dir


class DerivedAttributesTests:
    """ Tests for the behavior of Project's derived_attributes attribute. """

    ADDITIONAL_DERIVED_ATTRIBUTES = ["arbitrary1", "filler2", "placeholder3"]
    DERIVED_ATTRIBUTES_CASE_TYPES = ["implicit", "disjoint", "intersection"]

    def create_project(
            self, project_config_data, case_type, dirpath):
        """
        For a test case, determine expectations and create Project instance.
        
        :param dict project_config_data: the actual data to write to the 
            Project configuration file
        :param str default_env_path: path to the default environment config 
            file to pass to Project constructor
        :param str case_type: type of test case to execute; this determines 
            how to specify the derived attribute in the config file
        :param str dirpath: path in which to write config file
        :return (Iterable[str], Project): collection of names of derived 
            attribute to expect, along with Project instance with which to test
        """

        # Ensure valid parameterization.
        if case_type not in self.DERIVED_ATTRIBUTES_CASE_TYPES:
            raise ValueError(
                "Unexpected derived_attributes case type: '{}' (known={})".
                format(case_type, self.DERIVED_ATTRIBUTES_CASE_TYPES))

        # Parameterization specifies expectation and explicit specification.
        expected_derived_attributes = copy.copy(Project.DERIVED_ATTRIBUTES_DEFAULT)
        if case_type == "implicit":
            # Negative control; ensure config data lacks derived attributes.
            assert "derived_attributes" not in project_config_data
        else:
            explicit_derived_attributes = \
                    copy.copy(self.ADDITIONAL_DERIVED_ATTRIBUTES)
            expected_derived_attributes.extend(self.ADDITIONAL_DERIVED_ATTRIBUTES)
            # Determine explicit inclusion of default derived attributes.
            if case_type == "intersection":
                explicit_derived_attributes.extend(
                        Project.DERIVED_ATTRIBUTES_DEFAULT)
            project_config_data["derived_attributes"] = explicit_derived_attributes

        # Write the config and build the Project.
        conf_file_path = _write_project_config(
                project_config_data, dirpath=dirpath)
        with mock.patch("peppy.project.Project.parse_sample_sheet"):
            project = Project(conf_file_path)
        return expected_derived_attributes, project

    def test_default_derived_attributes_always_present(self,
            env_config_filepath, project_config_data, case_type, tmpdir):
        """ Explicit or implicit, default derived attributes are always there. """

        expected_derived_attributes, project = self.create_project(
                project_config_data=project_config_data,
                case_type=case_type, dirpath=tmpdir.strpath)

        # Rough approximation of order-agnostic validation of
        # presence and number agreement for all elements.
        assert len(expected_derived_attributes) == len(project.derived_attributes)
        assert set(expected_derived_attributes) == set(project.derived_attributes)

    def test_default_derived_attributes_not_duplicated(self,
            env_config_filepath, project_config_data, case_type, tmpdir):
        """ Default derived attributes are not added if already present. """
        from collections import Counter
        _, project = self.create_project(
                project_config_data=project_config_data,
                case_type=case_type, dirpath=tmpdir.strpath)
        num_occ_by_derived_attribute = Counter(project.derived_attributes)
        for default_derived_colname in Project.DERIVED_ATTRIBUTES_DEFAULT:
            assert 1 == num_occ_by_derived_attribute[default_derived_colname]


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
        with mock.patch("peppy.project.Project.parse_sample_sheet"):
            project = Project(conf_file_path)

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
        """ Samples in merge file, check data_sources --> derived_attributes. """
        # Order may be lost due to mapping.
        # We don't care about that here, or about duplicates.
        required = set(DERIVED_COLNAMES)
        observed = {k for k in proj.samples[sample_index].merged_cols.keys()
                    if k != "col_modifier" and not k.endswith(COL_KEY_SUFFIX)}
        # Observed may include additional things (like auto-added subsample_name)
        assert required == (required & observed)

    @named_param(argnames="sample_index", argvalues=MERGED_SAMPLE_INDICES)
    def test_derived_attributes_sample_subannotation_sample(
            self, proj, sample_index):
        """ Make sure derived attributes works on merged table. """
        observed_merged_sample_filepaths = \
            [os.path.basename(f) for f in
             proj.samples[sample_index].file2.split(" ")]
        assert EXPECTED_MERGED_SAMPLE_FILES == \
               observed_merged_sample_filepaths

    @named_param(argnames="sample_index",
                 argvalues=set(range(NUM_SAMPLES)) - MERGED_SAMPLE_INDICES)
    def test_unmerged_samples_lack_merged_cols(self, proj, sample_index):
        """ Samples not in the `subsample_table` lack merged columns. """
        # Assert the negative to cover empty dict/AttMap/None/etc.
        assert not proj.samples[sample_index].merged_cols

    def test_duplicate_derived_attributes_still_derived(self, proj):
        """ Duplicated derived attributes can still be derived. """
        sample_index = 2
        observed_nonmerged_col_basename = \
            os.path.basename(proj.samples[sample_index].nonmerged_col)
        assert "c.txt" == observed_nonmerged_col_basename
        assert "" == proj.samples[sample_index].locate_data_source(
                proj.data_sources, 'file')


class SubprojectActivationDeactivationTest:
    """ Test cases for the effect of activating/deactivating a subproject. """

    MARK_NAME = "marker"
    SUBPROJ_SECTION = {
        "neurons": {MARK_NAME: "NeuN"}, "astrocytes": {MARK_NAME: "GFAP"},
        "oligodendrocytes": {MARK_NAME: "NG2"}, "microglia": {MARK_NAME: "Iba1"}
    }

    @pytest.mark.parametrize("sub", SUBPROJ_SECTION.keys())
    def test_subproj_activation_returns_project(self, tmpdir, sub):
        """ Subproject activation returns the project instance. """
        prj = self.make_proj(tmpdir.strpath, incl_subs=True)
        updated_prj = prj.activate_subproject(sub)
        assert updated_prj is prj

    @pytest.mark.parametrize("sub", [None])
    def test_subproj_activation_errors_on_none(self, tmpdir, sub):
        """ Subproject deactivation returns raises TypeError when input is NoneType. """
        prj = self.make_proj(tmpdir.strpath, incl_subs=True)
        with pytest.raises(TypeError):
            prj.activate_subproject(sub)

    @pytest.mark.parametrize("sub", SUBPROJ_SECTION.keys())
    def test_subproj_deactivation_returns_project(self, tmpdir, sub):
        """ Subproject deactivation returns the project instance. """
        prj = self.make_proj(tmpdir.strpath, incl_subs=True)
        updated_prj = prj.activate_subproject(sub)
        deactivated_subprj = updated_prj.deactivate_subproject()
        assert deactivated_subprj is prj

    @pytest.mark.parametrize("sub", SUBPROJ_SECTION.keys())
    def test_subproj_deactivation_doesnt_change_project(self, tmpdir, sub):
        """ Activation and deactivation of a subproject restores original. """
        prj = self.make_proj(tmpdir.strpath, incl_subs=True)
        updated_prj = prj.activate_subproject(sub)
        deactivated_subprj = updated_prj.deactivate_subproject()
        assert deactivated_subprj == prj

    @pytest.mark.parametrize("sub", SUBPROJ_SECTION.keys())
    def test_subproj_activation_changes_subproject_attr(self, tmpdir, sub):
        """ Subproject activation populates a project's subproject field. """
        prj = self.make_proj(tmpdir.strpath, incl_subs=True)
        updated_prj = prj.activate_subproject(sub)
        assert updated_prj.subproject is not None

    @pytest.mark.parametrize("sub", SUBPROJ_SECTION.keys())
    def test_subproj_deactivation_changes_subproject_attr_to_none(self, tmpdir, sub):
        """ Subproject deactivation nullifies the subproject field. """
        prj = self.make_proj(tmpdir.strpath, incl_subs=True)
        updated_prj = prj.activate_subproject(sub)
        deactivated_subprj = updated_prj.deactivate_subproject()
        assert deactivated_subprj.subproject is None

    @pytest.mark.parametrize(
        ["super_data", "sub_data", "preserved"],
        [({"a": "1", "b": "2"}, {"c": "3"}, ["a", "b"]),
         ({"a": "1", "b": "2"}, {"b": "1"}, ["a"])]
    )
    def test_sp_act_preserves_nonoverlapping_entries(
            self, tmpdir, super_data, sub_data, preserved):
        """ Existing entries not in subproject should be kept as-is. """
        sp = "sub"
        meta_key = METADATA_KEY
        conf_data = {meta_key: super_data,
                     SUBPROJECTS_SECTION: {sp: {meta_key: sub_data}}}
        conf_file = tmpdir.join("conf.yaml").strpath
        with open(conf_file, 'w') as f:
            yaml.dump(conf_data, f)
        p = Project(conf_file)
        originals = [(k, p[meta_key][k]) for k in preserved]
        print("INITIAL METADATA: {}".format(p.metadata))
        p = p.activate_subproject(sp)
        print("UPDATED METADATA: {}".format(p.metadata))
        for k, v in originals:
            assert v == p[meta_key][k]

    @pytest.mark.parametrize("sub", SUBPROJ_SECTION.keys())
    def test_subproj_activation_adds_new_config_entries(self, tmpdir, sub):
        """ Previously nonexistent entries are added by subproject. """
        prj = self.make_proj(tmpdir.strpath, incl_subs=True)
        assert self.MARK_NAME not in prj
        prj.activate_subproject(sub)
        assert self.MARK_NAME in prj
        assert self.SUBPROJ_SECTION[sub][self.MARK_NAME] == prj[self.MARK_NAME]

    @pytest.mark.parametrize("sub", SUBPROJ_SECTION.keys())
    def test_sp_act_overwrites_existing_config_entries(self, tmpdir, sub):
        """ An activated subproject's values are favored over preexisting. """
        prj = self.make_proj(tmpdir.strpath, incl_subs=True)
        prj[self.MARK_NAME] = "temp-mark"
        assert "temp-mark" == prj[self.MARK_NAME]
        prj.activate_subproject(sub)
        expected = self.SUBPROJ_SECTION[sub][self.MARK_NAME]
        assert expected == prj[self.MARK_NAME]

    def test_activate_unknown_subproj(self, tmpdir):
        """ With subprojects, attempt to activate undefined one is an error. """
        prj = self.make_proj(tmpdir.strpath, incl_subs=True)
        with pytest.raises(Exception):
            prj.activate_subproject("DNE-subproject")

    @pytest.mark.parametrize("sub", SUBPROJ_SECTION.keys())
    def test_subproj_activation_when_none_exist(self, tmpdir, sub):
        """ Without subprojects, activation attempt produces warning. """
        prj = self.make_proj(tmpdir.strpath, incl_subs=False)
        with pytest.raises(MissingSubprojectError):
            prj.activate_subproject(sub)

    @classmethod
    def make_proj(cls, folder, incl_subs):
        """ Write temp config and create Project with subproject option. """
        conf_file_path = os.path.join(folder, "conf.yaml")
        conf_data = {METADATA_KEY: {}}
        if incl_subs:
            conf_data.update(**{SUBPROJECTS_SECTION: cls.SUBPROJ_SECTION})
        with open(conf_file_path, 'w') as f:
            yaml.safe_dump(conf_data, f)
        return Project(conf_file_path)


@pytest.mark.usefixtures("write_project_files")
class ProjectWarningTests:
    """ Tests for warning messages related to projects """

    @pytest.mark.parametrize(
        "ideally_implied_mappings",
        [{}, {GENOMES_KEY: _GENOMES}, {TRANSCRIPTOMES_KEY: _TRANSCRIPTOMES},
         {GENOMES_KEY: _GENOMES, TRANSCRIPTOMES_KEY: _TRANSCRIPTOMES}])
    def test_suggests_implied_attributes(
        self, recwarn, tmpdir, path_sample_anns,
        project_config_data, ideally_implied_mappings):
        """ Assemblies directly in proj conf (not implied) is deprecated. """

        # Add the mappings parameterization to the config data.
        conf_data = copy.deepcopy(project_config_data)
        conf_data.update(ideally_implied_mappings)

        # Write the config file.
        conf_file = tmpdir.join("proj_conf.yaml").strpath
        assert not os.path.isfile(conf_file), \
            "Test project temp config file already exists: {}".format(conf_file)
        with open(conf_file, 'w') as cf:
            yaml.safe_dump(conf_data, cf)

        # (Hopefully) generate the warnings.
        assert 0 == len(recwarn)           # Ensure a fresh start.
        warnings.simplefilter('always')    # Allow DeprecationWarning capture.
        Project(conf_file)                 # Generate the warning(s).
        msgs = [str(w.message) for w in recwarn    # Grab deprecation messages.
                if isinstance(w.message, DeprecationWarning)]
        assert len(ideally_implied_mappings) == len(msgs)    # 1:1 warnings
        for k in ideally_implied_mappings:
            # Each section that should be implied should generate exactly 1
            # warning; check message for content then remove it from the pool.
            matched = [m for m in msgs if k in m and
                       IMPLICATIONS_DECLARATION in m]
            assert 1 == len(matched)
            msgs.remove(matched[0])

    @pytest.mark.parametrize("assembly_implications",
        [{"genome": {"organism": _GENOMES}},
         {"transcriptome": {"organism": _TRANSCRIPTOMES}},
         {"genome": {"organism": _GENOMES},
           "transcriptome": {"organism": _TRANSCRIPTOMES}}])
    def test_no_warning_if_assemblies_are_implied(
        self, recwarn, tmpdir, path_sample_anns,
        project_config_data, assembly_implications):
        """ Assemblies declaration within implied columns is not deprecated. """

        # Add the mappings parameterization to the config data.
        conf_data = copy.deepcopy(project_config_data)
        conf_data[IMPLICATIONS_DECLARATION] = assembly_implications

        # Write the config file.
        conf_file = tmpdir.join("proj_conf.yaml").strpath
        assert not os.path.isfile(conf_file), \
            "Test project temp config file already exists: {}".format(conf_file)
        with open(conf_file, 'w') as cf:
            yaml.safe_dump(conf_data, cf)

        # Check that there are no warnings before or after test.
        assert 0 == len(recwarn)
        warnings.simplefilter('always')
        Project(conf_file)
        num_yaml_warns = sum(1 for w in recwarn if
                             issubclass(w.category, yaml.YAMLLoadWarning))
        assert 0 == (len(recwarn) - num_yaml_warns)


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
