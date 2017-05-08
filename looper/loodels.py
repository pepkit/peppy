""" Looper versions of NGS project models. """

import models


__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"



class Project(models.Project):
    """ Looper-specific NGS Project. """


    @property
    def required_metadata(self):
        return ["output_dir"]


    @property
    def project_folders(self):
        return ["output_dir", "results_subdir", "submission_subdir"]


    @property
    def output_dir(self):
        return self.metadata.output_dir


    @staticmethod
    def infer_name(path_config_file):
        import os
        metadata_folder_path = os.path.dirname(path_config_file)
        proj_root_path, _ = os.path.split(metadata_folder_path)
        _, proj_root_name = os.path.split(proj_root_path)
        return proj_root_name


    def add_sample_sheet(self, csv=None):
        # Derived columns: by default, use data_source
        if hasattr(self, "derived_columns"):
            # Do not duplicate!
            if "data_source" not in self.derived_columns:
                self.derived_columns.append("data_source")
        else:
            self.derived_columns = ["data_source"]
        super(Project, self).add_sample_sheet(csv)