"""
Build a Project object.
"""

from attmap import PathExAttMap
import pandas as pd

READ_CSV_KWARGS = {"engine": "python", "dtype": str, "index_col": False,
                   "keep_default_na": False, "na_values": [""]}

@copy
class Project2(PathExAttMap):
    """
    A class to model a Project (collection of samples and metadata).

    :param str | Mapping cfg: Project config file (YAML), or appropriate
        key-value mapping of data to constitute project
    :param str subproject: Subproject to use within configuration file, optional
    :param bool defer_sample_construction: whether to wait to build this Project's
        Sample objects until they're needed, optional; by default, the basic
        Sample is created during Project construction

    :Example:

    .. code-block:: python

        from models import Project
        prj = Project("config.yaml")

    """

    # Hook for Project's declaration of how it identifies samples.
    # Used for validation and for merge_sample (derived cols and such)
    SAMPLE_NAME_IDENTIFIER = SAMPLE_NAME_COLNAME

    DERIVED_ATTRIBUTES_DEFAULT = [DATA_SOURCE_COLNAME]

    def __init__(self, cfg, subproject=None, defer_sample_construction=False,
    			 **kwargs):
    	super(Project2, self).__init__()
    	self.parsed = PathExAttMap()
    	self.load_samples()
    	self.modify_samples()

    def load_samples:
    	if self.sample_table:
    		df = pd.read_csv(self.sample_table, 
    						 sep=infer_delimiter(self.sample_table),
    						 **READ_CSV_KWARGS)
    		self.parsed.sample_table = df
    	else:
    		_LOGGER-warning("No sample table specified.")

		if self.subsample_table:
			df = read_csv(self.subsample_table,
						  sep=infer_delimiter(self.subsample_table),
						  **READ_CSV_KWARGS)


    def modify_samples:

    	self.attr_constants()
    	self.attr_synonyms()
    	self.attr_imply()
    	self.attr_derive()

    def attr_imply:
    	pass

    def attr_synonyms:
    	pass

    def attr_constants:
    	pass

	def attr_derive:
		pass 

	def __repr__:
		pass



def infer_delimiter(filepath):
    """
    From extension infer delimiter used in a separated values file.

    :param str filepath: path to file about which to make inference
    :return str | NoneType: extension if inference succeeded; else null
    """
    ext = os.path.splitext(filepath)[1][1:].lower()
    return {"txt": "\t", "tsv": "\t", "csv": ","}.get(ext)
