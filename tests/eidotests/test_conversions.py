from peppy.eido.conversion import (
    convert_project,
    get_available_pep_filters,
    pep_conversion_plugins,
    run_filter,
)
from peppy.eido.output_formatters import MultilineOutputFormatter
from peppy.project import Project
from peppy.sample import Sample


class TestConversionInfrastructure:
    def test_plugins_are_read(self):
        avail_filters = get_available_pep_filters()
        assert isinstance(avail_filters, list)

    def test_plugins_contents(self):
        avail_plugins = pep_conversion_plugins()
        avail_filters = get_available_pep_filters()
        assert all(
            [plugin_name in avail_filters for plugin_name in avail_plugins.keys()]
        )

    def test_plugins_are_callable(self):
        avail_plugins = pep_conversion_plugins()
        assert all(
            [callable(plugin_fun) for plugin_name, plugin_fun in avail_plugins.items()]
        )

    def test_basic_filter(self, save_result_mock, project_object):
        conv_result = run_filter(
            project_object,
            "basic",
            verbose=False,
            plugin_kwargs={"paths": {"project": "out/basic_prj.txt"}},
        )

        assert save_result_mock.called
        assert conv_result["project"] == str(project_object)

    def test_csv_filter(
        self, save_result_mock, taxprofiler_project, taxprofiler_csv_multiline_output
    ):
        conv_result = run_filter(
            taxprofiler_project,
            "csv",
            verbose=False,
            plugin_kwargs={"paths": {"samples": "out/basic_prj.txt"}},
        )

        assert save_result_mock.called
        assert conv_result["samples"] == taxprofiler_csv_multiline_output

    def test_csv_filter_handles_empty_fasta_correctly(
        self,
        project_pep_with_fasta_column,
        output_pep_with_fasta_column,
        save_result_mock,
    ):
        conv_result = run_filter(
            project_pep_with_fasta_column,
            "csv",
            verbose=False,
            plugin_kwargs={"paths": {"samples": "out/basic_prj.txt"}},
        )

        assert save_result_mock.called
        assert conv_result == {"samples": output_pep_with_fasta_column}

    def test_eido_csv_filter_filters_nextflow_taxprofiler_input_correctly(
        self,
        project_pep_nextflow_taxprofiler,
        output_pep_nextflow_taxprofiler,
        save_result_mock,
    ):
        conv_result = run_filter(
            project_pep_nextflow_taxprofiler,
            "csv",
            verbose=False,
            plugin_kwargs={"paths": {"samples": "out/basic_prj.txt"}},
        )

        assert save_result_mock.called
        assert conv_result == {"samples": output_pep_nextflow_taxprofiler}

    def test_multiple_subsamples(self, test_multiple_subs):
        project = Project(test_multiple_subs, sample_table_index="sample_id")

        conversion = convert_project(
            project,
            "csv",
        )
        assert isinstance(conversion["samples"], str)
        conversion = convert_project(
            project,
            "basic",
        )
        assert isinstance(conversion["project"], str)
        conversion = convert_project(
            project,
            "yaml",
        )
        assert isinstance(conversion["project"], str)
        conversion = convert_project(
            project,
            "yaml-samples",
        )
        assert isinstance(conversion["samples"], str)


class TestMultilineOutputFormatterMissingValues:
    """
    Under pandas >=3.0 a missing attribute reaches the formatter as float('nan')
    rather than as an empty string, which used to raise TypeError from the join.
    """

    def test_missing_attribute_becomes_empty_field(self):
        sample = Sample({"sample": "frog_1", "fasta": float("nan")})

        assert MultilineOutputFormatter.format([sample]) == "sample,fasta\nfrog_1,\n"

    def test_missing_subsample_attribute_becomes_empty_field(self):
        # Merging a subsample table that lacks a column produces a list of nan
        sample = Sample(
            {
                "sample": "frog_1",
                "fasta": [float("nan"), float("nan")],
                "subsample_name": ["0", "1"],
            }
        )

        assert (
            MultilineOutputFormatter.format([sample])
            == "sample,fasta\nfrog_1,\nfrog_1,\n"
        )
