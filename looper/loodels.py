""" Looper versions of NGS project models. """

import models


__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"



class Project(models.Project):

    def add_sample_sheet(self, csv=None):
        # Derived columns: by default, use data_source
        if hasattr(self, "derived_columns"):
            # Do not duplicate!
            if "data_source" not in self.derived_columns:
                self.derived_columns.append("data_source")
        else:
            self.derived_columns = ["data_source"]
        super(Project, self).add_sample_sheet(csv)