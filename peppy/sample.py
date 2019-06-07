""" Modeling individual samples to process or otherwise use. """

from collections import OrderedDict
import glob
import os
import sys
if sys.version_info < (3, 3):
    from collections import Mapping
else:
    from collections.abc import Mapping
import warnings

from pandas import isnull, Series
import yaml

from attmap import AttMap, PathExAttMap
from .const import *
from .const import SNAKEMAKE_SAMPLE_COL
from .utils import copy, get_logger, get_name_depr_msg, grab_project_data, \
    sample_folder

COL_KEY_SUFFIX = "_key"
PRJ_REF = "prj"
_OLD_PROTOCOL_REF = "library"


__all__ = ["merge_sample", "Paths", "Sample", "Subsample"]


_LOGGER = get_logger(__name__)


@copy
class Subsample(PathExAttMap):
    """
    Class to model Subsamples.

    A Subsample is a component of a sample. They are typically used for samples
    that have multiple input files of the same type, and are specified in the
    PEP by a subannotation table. Each row in the subannotation (or unit) table
    corresponds to a Subsample object.

    :param Mapping | pandas.core.series.Series series: Subsample data
    """
    def __init__(self, series, sample=None):
        data = OrderedDict(series)
        _LOGGER.debug("Subsample data:\n{}".format(data))
        super(Subsample, self).__init__(entries=data)
        self.sample = sample


@copy
class Sample(PathExAttMap):
    """
    Class to model Samples based on a pandas Series.

    :param Mapping | pandas.core.series.Series series: Sample's data.

    :Example:

    .. code-block:: python

        from models import Project, SampleSheet, Sample
        prj = Project("ngs")
        sheet = SampleSheet("~/projects/example/sheet.csv", prj)
        s1 = Sample(sheet.iloc[0])
    """

    _FEATURE_ATTR_NAMES = ["read_length", "read_type", "paired"]

    # Originally, this object was inheriting from Series,
    # but complications with serializing and code maintenance
    # made me go back and implement it as a top-level object
    def __init__(self, series, prj=None):

        super(Sample, self).__init__()

        # Create data, handling library/protocol.
        data = OrderedDict(series)

        # Handle assay representation (protocol vs. library).
        try:
            protocol = data.pop(_OLD_PROTOCOL_REF)
        except KeyError:
            pass
        else:
            msg = get_name_depr_msg(_OLD_PROTOCOL_REF, ASSAY_KEY, self.__class__)
            warnings.warn(msg, DeprecationWarning)
            data[ASSAY_KEY] = protocol

        # Handle Snakemake vs. native peppy naming convention.
        try:
            name_sm = data.pop(SNAKEMAKE_SAMPLE_COL)
        except:
            pass    # No Snakemake sample identifier key.
        else:
            try:
                name_pep = data[SAMPLE_NAME_COLNAME]
            except KeyError:
                _LOGGER.whisper("Renaming {} to {}".format(
                    SNAKEMAKE_SAMPLE_COL, SAMPLE_NAME_COLNAME))
                data = OrderedDict(
                    [(SAMPLE_NAME_COLNAME, name_sm)] + list(data.items()))
            else:
                if name_pep == name_sm:
                    _LOGGER.whisper(
                        "Used two sample identifiers ({} and {})".format(
                            SAMPLE_NAME_COLNAME, SNAKEMAKE_SAMPLE_COL))
                else:
                    raise Exception(
                        "Attempted to build sample with discordant identifier "
                        "keys ({smk}={smv} and {pk}={pv})".format(
                            smk=SNAKEMAKE_SAMPLE_COL, smv=name_sm,
                            pk=SAMPLE_NAME_COLNAME, pv=name_pep))

        _LOGGER.whisper("Sample data: {}".format(data))
        self.add_entries(data)

        if PRJ_REF in self and prj:
            _LOGGER.warn("Project provided both directly and indirectly; "
                         "using direct")
        if prj or PRJ_REF not in self:
            self[PRJ_REF] = prj or None

        assert self[PRJ_REF] is None or isinstance(self[PRJ_REF], AttMap), \
            "Project reference must be null or {}; got {}".format(AttMap.__name__, type(self[PRJ_REF]))

        self.merged_cols = {}
        self.derived_cols_done = []

        if isinstance(series, Series):
            series = series.to_dict(OrderedDict)
        elif isinstance(series, Sample):
            series = series.as_series().to_dict(OrderedDict)

        # Keep a list of attributes that came from the sample sheet,
        # so we can create a minimal, ordered representation of the original.
        # This allows summarization of the sample (i.e.,
        # appending new columns onto the original table)
        self.sheet_attributes = list(series.keys())

        # Check if required attributes exist and are not empty.
        missing_attributes_message = self.check_valid()
        if missing_attributes_message:
            raise ValueError(missing_attributes_message)

        self.name = self.sample_name

        # Default to no required paths and no YAML file.
        self.required_paths = None
        self.yaml_file = None

        # Not yet merged, potentially toggled when merge step is considered.
        self.merged = False

        # Collect sample-specific filepaths.
        # Only when sample is added to project, can paths be added.
        # Essentially, this provides an empty container for tool-specific
        # filepaths, into which a pipeline may deposit such filepaths as
        # desired. Such use provides a sort of communication interface
        # between times and perhaps individuals (processing time vs.
        # analysis time, and a pipeline author vs. a pipeline user).
        self.paths = Paths()

    def _excl_from_eq(self, k):
        """ Exclude the Project reference from object comparison. """
        return k == PRJ_REF or super(Sample, self)._excl_from_eq(k)

    def _excl_from_repr(self, k, cls):
        """ Exclude the Project reference from representation. """
        # TODO: better solution for this cyclical dependency hack
        return k == PRJ_REF or super(Sample, self)._excl_from_repr(k, cls)

    def __setitem__(self, key, value):
        # TODO: better solution for this cyclical dependency hack
        if value.__class__.__name__ == "Project":
            self.__dict__[key] = value
        else:
            super(Sample, self).__setitem__(key, value)

    def __str__(self):
        return "{} '{}'".format(self.__class__.__name__, self.name)

    @property
    def input_file_paths(self):
        """
        List the sample's data source / input files

        :return list[str]: paths to data sources / input file for this Sample.
        """
        return self.data_source.split(" ") if self.data_source else []

    def as_series(self):
        """
        Returns a `pandas.Series` object with all the sample's attributes.

        :return pandas.core.series.Series: pandas Series representation
            of this Sample, with its attributes.
        """
        # Note that this preserves metadata, but it could be excluded
        # with self.items() rather than self.__dict__.
        return Series(self.__dict__)

    def check_valid(self, required=None):
        """
        Check provided sample annotation is valid.

        :param Iterable[str] required: collection of required sample attribute
            names, optional; if unspecified, only a name is required.
        :return (Exception | NoneType, str, str): exception and messages about
            what's missing/empty; null with empty messages if there was nothing
            exceptional or required inputs are absent or not set
        """
        missing, empty = [], []
        for attr in (required or [SAMPLE_NAME_COLNAME]):
            if attr not in self:
                missing.append(attr)
            if attr == "nan":
                empty.append(attr)
        missing_attributes_message = \
            "Sample lacks attribute(s). missing={}; empty={}". \
                format(missing, empty) if (missing or empty) else ""
        return missing_attributes_message

    def generate_filename(self, delimiter="_"):
        """
        Create a name for file in which to represent this Sample.

        This uses knowledge of the instance's subtype, sandwiching a delimiter
        between the name of this Sample and the name of the subtype before the
        extension. If the instance is a base Sample type, then the filename
        is simply the sample name with an extension.

        :param str delimiter: what to place between sample name and name of
            subtype; this is only relevant if the instance is of a subclass
        :return str: name for file with which to represent this Sample on disk
        """
        base = self.name if type(self) is Sample else \
            "{}{}{}".format(self.name, delimiter, self.__class__.__name__)
        return "{}.yaml".format(base)

    def generate_name(self):
        """
        Generate name for the sample by joining some of its attribute strings.
        """
        raise NotImplementedError("Not implemented in new code base.")

    def get_attr_values(self, attrlist):
        """
        Get value corresponding to each given attribute.

        :param str attrlist: name of an attribute storing a list of attr names
        :return list | NoneType: value (or empty string) corresponding to
            each named attribute; null if this Sample's value for the
            attribute given by the argument to the "attrlist" parameter is
            empty/null, or if this Sample lacks the indicated attribute
        """
        # If attribute is None, then value is also None.
        attribute_list = getattr(self, attrlist, None)
        if not attribute_list:
            return None

        if not isinstance(attribute_list, list):
            attribute_list = [attribute_list]

        # Strings contained here are appended later so shouldn't be null.
        return [getattr(self, attr, "") for attr in attribute_list]

    def get_sheet_dict(self):
        """
        Create a K-V pairs for items originally passed in via the sample sheet.

        This is useful for summarizing; it provides a representation of the
        sample that excludes things like config files and derived entries.

        :return OrderedDict: mapping from name to value for data elements
            originally provided via the sample sheet (i.e., the a map-like
            representation of the instance, excluding derived items)
        """
        return OrderedDict(
            [[k, getattr(self, k)] for k in self.sheet_attributes])

    def infer_attributes(self, implications):
        """
        Infer value for additional field(s) from other field(s).

        Add columns/fields to the sample based on values in those already-set
        that the sample's project defines as indicative of implications for
        additional data elements for the sample.

        :param Mapping implications: Project's implied columns data
        :return None: this function mutates state and is strictly for effect
        """

        _LOGGER.log(5, "Sample attribute implications: {}".
                    format(implications))
        if not implications:
            return

        for implier_name, implied in implications.items():
            _LOGGER.debug(
                "Setting Sample variable(s) implied by '%s'", implier_name)
            try:
                implier_value = self[implier_name]
            except KeyError:
                _LOGGER.debug("No '%s' for this sample", implier_name)
                continue
            try:
                implied_value_by_column = implied[implier_value]
                _LOGGER.debug("Implications for '%s' = %s: %s",
                              implier_name, implier_value,
                              str(implied_value_by_column))
                for colname, implied_value in \
                        implied_value_by_column.items():
                    _LOGGER.log(5, "Setting '%s'=%s",
                                colname, implied_value)
                    self.__setitem__(colname, implied_value)
            except KeyError:
                _LOGGER.log(
                    5, "Unknown implied value for implier '%s' = '%s'",
                    implier_name, implier_value)

    def is_dormant(self):
        """
        Determine whether this Sample is inactive.

        By default, a Sample is regarded as active. That is, if it lacks an
        indication about activation status, it's assumed to be active. If,
        however, and there's an indication of such status, it must be '1'
        in order to be considered switched 'on.'

        :return bool: whether this Sample's been designated as dormant
        """
        try:
            flag = self[SAMPLE_EXECUTION_TOGGLE]
        except KeyError:
            # Regard default Sample state as active.
            return False
        # If specified, the activation flag must be set to '1'.
        return flag != "1"

    @property
    def library(self):
        """
        Backwards-compatible alias.

        :return str: The protocol / NGS library name for this Sample.
        """
        warnings.warn(get_name_depr_msg(
            _OLD_PROTOCOL_REF, ASSAY_KEY, self.__class__), DeprecationWarning)
        return self.protocol

    def get_subsample(self, subsample_name):
        """
        Retrieve a single subsample by name.

        :param str subsample_name: The name of the desired subsample. Should 
            match the subsample_name column in the subannotation sheet.
        :return peppy.Subsample: Requested Subsample object
        """
        subsamples = self.get_subsamples([subsample_name])
        if len(subsamples) > 1:
            _LOGGER.error("More than one subsample with that name.")
        try:
            return subsamples[0]
        except IndexError:
            raise ValueError("Sample {} has no subsample named {}.".
                             format(self.name, subsample_name))

    def get_subsamples(self, subsample_names):
        """
        Retrieve subsamples assigned to this sample

        :param list[str] subsample_names: List of names of subsamples to retrieve
        :return list[peppy.Subsample]: List of subsamples
        """
        return [s for s in self.subsamples if s.subsample_name in subsample_names]

    def locate_data_source(self, data_sources, column_name=DATA_SOURCE_COLNAME,
                           source_key=None, extra_vars=None):
        """
        Uses the template path provided in the project config section
        "data_sources" to piece together an actual path by substituting
        variables (encoded by "{variable}"") with sample attributes.

        :param Mapping data_sources: mapping from key name (as a value in
            a cell of a tabular data structure) to, e.g., filepath
        :param str column_name: Name of sample attribute
            (equivalently, sample sheet column) specifying a derived column.
        :param str source_key: The key of the data_source,
            used to index into the project config data_sources section.
            By default, the source key will be taken as the value of
            the specified column (as a sample attribute).
            For cases where the sample doesn't have this attribute yet
            (e.g. in a merge table), you must specify the source key.
        :param dict extra_vars: By default, this will look to
            populate the template location using attributes found in the
            current sample; however, you may also provide a dict of extra
            variables that can also be used for variable replacement.
            These extra variables are given a higher priority.
        :return str: regex expansion of data source specified in configuration,
            with variable substitutions made
        :raises ValueError: if argument to data_sources parameter is null/empty
        """

        if not data_sources:
            return None

        if not source_key:
            try:
                source_key = getattr(self, column_name)
            except AttributeError:
                reason = "'{attr}': to locate sample's data source, provide " \
                         "the name of a key from '{sources}' or ensure " \
                         "sample has attribute '{attr}'".format(
                    attr=column_name, sources=DATA_SOURCES_SECTION)
                raise AttributeError(reason)

        try:
            regex = data_sources[source_key]
        except KeyError:
            _LOGGER.debug(
                "{}: config lacks entry for data_source key: '{}' "
                "in column '{}'; known: {}".format(
                    self.name, source_key, column_name, data_sources.keys()))
            return ""

        # Populate any environment variables like $VAR with os.environ["VAR"]
        # Now handled upstream, in project.
        #regex = os.path.expandvars(regex)

        try:
            # Grab a temporary dictionary of sample attributes and update these
            # with any provided extra variables to use in the replacement.
            # This is necessary for derived_attributes in the merge table.
            # Here the copy() prevents the actual sample from being
            # updated by update().
            temp_dict = dict(self.items())
            temp_dict.update(extra_vars or dict())
            val = regex.format(**temp_dict)
            if '*' in val or '[' in val:
                _LOGGER.debug("Pre-glob: %s", val)
                val_globbed = sorted(glob.glob(val))
                if not val_globbed:
                    _LOGGER.debug("No files match provided glob: '%s'", val)
                else:
                    val = " ".join(val_globbed)
                _LOGGER.debug("Post-glob: %s", val)

        except Exception as e:
            _LOGGER.error("Cannot correctly format data source ({}): {} -- {}".
                          format(str(type(e).__name__), str(e), regex))
            return regex

        return val

    def make_sample_dirs(self):
        """
        Creates sample directory structure if it doesn't exist.
        """
        for path in self.paths:
            if not os.path.exists(path):
                os.makedirs(path)

    def set_file_paths(self, project=None):
        """
        Sets the paths of all files for this sample.

        :param attmap.PathExAttMap project: object with pointers to data
            paths and such, either full Project or PathExAttMap with
            sufficient data
        """
        # Any columns specified as "derived" will be constructed
        # based on regex in the "data_sources" section of project config.

        project = project or self.prj

        derived = project.get("derived_attributes", [])
        for col in ([derived] if isinstance(derived, str) else derived):
            # Only proceed if the specified column exists
            # and was not already merged or derived.
            if not hasattr(self, col):
                _LOGGER.debug("%s lacks attribute '%s'", self.name, col)
                continue
            elif col in self.merged_cols:
                _LOGGER.debug("'%s' is already merged for %s", col, self.name)
                continue
            elif col in self.derived_cols_done:
                _LOGGER.debug("'%s' has been derived for %s", col, self.name)
                continue
            _LOGGER.debug("Deriving column for %s '%s': '%s'",
                          self.__class__.__name__, self.name, col)

            # Set a variable called {col}_key, so the
            # original source can also be retrieved.
            col_key = col + COL_KEY_SUFFIX
            col_key_val = getattr(self, col)
            _LOGGER.debug("Setting '%s' to '%s'", col_key, col_key_val)
            setattr(self, col_key, col_key_val)

            # Determine the filepath for the current data source and set that
            # attribute on this sample if it's non-empty/null.
            filepath = self.locate_data_source(
                data_sources=project.get(DATA_SOURCES_SECTION),
                column_name=col)
            if filepath:
                _LOGGER.debug("Setting '%s' to '%s'", col, filepath)
                setattr(self, col, filepath)
            else:
                _LOGGER.debug("Not setting null/empty value for data source "
                              "'{}': {}".format(col, type(filepath)))

            self.derived_cols_done.append(col)

        # Parent
        try:
            self.results_subdir = project.results_folder
        except AttributeError:
            self.results_subdir = project.metadata.results_subdir
        self.paths.sample_root = sample_folder(project, self)

        # Track url
        bigwig_filename = self.name + ".bigWig"
        try:
            # Project's public_html folder
            self.bigwig = os.path.join(
                project.trackhubs.trackhub_dir, bigwig_filename)
            self.track_url = \
                "{}/{}".format(project.trackhubs.url, bigwig_filename)
        except:
            _LOGGER.debug("No trackhub/URL")
            pass

    def set_genome(self, genomes):
        """
        Set the genome for this Sample.

        :param Mapping[str, str] genomes: genome assembly by organism name
        """
        self._set_assembly("genome", genomes)

    def set_transcriptome(self, transcriptomes):
        """
        Set the transcriptome for this Sample.

        :param Mapping[str, str] transcriptomes: transcriptome assembly by
            organism name
        """
        self._set_assembly("transcriptome", transcriptomes)

    def _set_assembly(self, ome, assemblies):
        if not assemblies:
            _LOGGER.debug("Empty/null assemblies mapping")
            return
        try:
            assembly = assemblies[self.organism]
        except AttributeError:
            _LOGGER.debug("Sample '%s' lacks organism attribute", self.name)
            assembly = None
        except KeyError:
            _LOGGER.log(5, "Unknown {} value: '{}'".
                        format(ome, self.organism))
            assembly = None
        _LOGGER.log(5, "Setting {} as {} on sample: '{}'".
                    format(assembly, ome, self.name))
        setattr(self, ome, assembly)

    def to_yaml(self, path=None, subs_folder_path=None, delimiter="_"):
        """
        Serializes itself in YAML format.

        :param str path: A file path to write yaml to; provide this or
            the subs_folder_path
        :param str subs_folder_path: path to folder in which to place file
            that's being written; provide this or a full filepath
        :param str delimiter: text to place between the sample name and the
            suffix within the filename; irrelevant if there's no suffix
        :return str: filepath used (same as input if given, otherwise the
            path value that was inferred)
        :raises ValueError: if neither full filepath nor path to extant
            parent directory is provided.
        """

        # Determine filepath, prioritizing anything given, then falling
        # back to a default using this Sample's Project's submission_subdir.
        # Use the sample name and YAML extension as the file name,
        # interjecting a pipeline name as a subfolder within the Project's
        # submission_subdir if such a pipeline name is provided.
        if not path:
            if not subs_folder_path:
                raise ValueError(
                    "To represent {} on disk, provide a full path or a path "
                    "to a parent (submissions) folder".
                        format(self.__class__.__name__))
            _LOGGER.debug("Creating filename for %s: '%s'",
                          self.__class__.__name__, self.name)
            filename = self.generate_filename(delimiter=delimiter)
            _LOGGER.debug("Filename: '%s'", filename)
            path = os.path.join(subs_folder_path, filename)

        _LOGGER.debug("Setting %s filepath: '%s'",
                      self.__class__.__name__, path)
        self.yaml_file = path

        def obj2dict(obj, name=None, 
                     to_skip=(SAMPLE_SUBANNOTATIONS_KEY, "samples",
                              NAME_TABLE_ATTR, "sheet_attributes")):
            """
            Build representation of object as a dict, recursively
            for all objects that might be attributes of self.

            :param object obj: what to serialize to write to YAML.
            :param str name: name of the object to represent.
            :param Iterable[str] to_skip: names of attributes to ignore.
            """
            if name:
                _LOGGER.log(5, "Converting to dict: '{}'".format(name))
            if name == PRJ_REF:
                _LOGGER.debug("Attempting to store %s's project data",
                              self.__class__.__name__)
                prj_data = grab_project_data(obj)
                _LOGGER.debug("Sample's project data: {}".format(prj_data))
                return {k: obj2dict(v, name=k) for k, v in prj_data.items()}
            if isinstance(obj, list):
                return [obj2dict(i) for i in obj]
            if isinstance(obj, AttMap):
                return {k: obj2dict(v, name=k) for k, v in obj.items()
                        if k not in to_skip}
            elif isinstance(obj, Mapping):
                return {k: obj2dict(v, name=k)
                        for k, v in obj.items() if k not in to_skip}
            elif isinstance(obj, Paths):
                return {k: obj2dict(v, name=k)
                        for k, v in obj.__dict__.items() if k not in to_skip}
            elif isinstance(obj, Series):
                _LOGGER.warning("Serializing series as mapping, not array-like")
                return obj.to_dict()
            elif hasattr(obj, 'dtype'):  # numpy data types
                # TODO: this fails with ValueError for multi-element array.
                return obj.item()
            elif isnull(obj):
                # Missing values as evaluated by pandas.isnull().
                # This gets correctly written into yaml.
                return "NaN"
            else:
                return obj

        _LOGGER.debug("Serializing %s: '%s'",
                      self.__class__.__name__, self.name)
        serial = obj2dict(self)

        # TODO: this is the way to add the project metadata reference if
        # the metadata items are to be accessed directly on the Sample rather
        # than through the Project; that is:
        #
        # sample.output_dir
        # instead of
        # sample.prj.output_dir
        #
        # In this case, "prj" should be added to the default argument to the
        # to_skip parameter in the function signature, and the instance check
        # of the object to serialize against Project can be dropped.
        """
        try:
            serial.update(self.prj.metadata)
        except AttributeError:
            _LOGGER.debug("%s lacks %s reference",
                          self.__class__.__name__, Project.__class__.__name__)
        else:
            _LOGGER.debug("Added %s metadata to serialized %s",
                          Project.__class__.__name__, self.__class__.__name__)
        """

        with open(self.yaml_file, 'w') as outfile:
            _LOGGER.debug("Generating YAML data for %s: '%s'",
                          self.__class__.__name__, self.name)
            try:
                yaml_data = yaml.safe_dump(serial, default_flow_style=False)
            except yaml.representer.RepresenterError:
                _LOGGER.error("SERIALIZED SAMPLE DATA: {}".format(serial))
                raise
            outfile.write(yaml_data)

    def update(self, newdata, **kwargs):
        """
        Update Sample object with attributes from a dict.
        """
        duplicates = [k for k in set(newdata.keys()) & set(kwargs.keys())
                      if newdata[k] != kwargs[k]]
        if len(duplicates) != 0:
            raise ValueError("{} duplicate keys with different values: {}".
                             format(len(duplicates), ", ".join(duplicates)))
        for k, v in newdata.items():
            setattr(self, k, v)
        for k, v in kwargs.items():
            setattr(self, k, v)


def merge_sample(sample, sample_subann, data_sources=None,
                 derived_attributes=None, sample_colname=SAMPLE_NAME_COLNAME):
    """
    Use merge table (subannotation) data to augment/modify Sample.

    :param Sample sample: sample to modify via merge table data
    :param pandas.core.frame.DataFrame sample_subann: data informing how to
        update given sample
    :param Mapping data_sources: collection of named paths to data locations,
        optional
    :param Iterable[str] derived_attributes: names of attributes for which
        corresponding Sample attribute's value is data-derived, optional
    :param str sample_colname: name of the designated sample name column
    :return peppy.Sample: updated Sample instance
    """

    merged_attrs = {}

    if sample_subann is None:
        _LOGGER.log(5, "No data for sample merge, skipping")
        return merged_attrs

    if sample_colname not in sample_subann.columns:
        alternative = SAMPLE_NAME_COLNAME
        _LOGGER.debug("'{}' is not a subannotation column; trying {}".
                      format(sample_colname, alternative))
        if alternative not in sample_subann.columns:
            raise KeyError(
                "Subannotation requires column '{}'.".format(sample_colname))
        sample_colname = alternative

    _LOGGER.debug("Using '{}' as sample name column from subannotation table".
                  format(sample_colname))
    _LOGGER.debug("Merging Sample with data sources: {}".
                  format(data_sources))

    # Hash derived columns for faster lookup in case of many samples/columns.
    derived_attributes = set(derived_attributes or [])
    _LOGGER.debug("Merging Sample with derived attributes: {}".
                  format(derived_attributes))

    sample_indexer = sample_subann[sample_colname] == sample.name
    this_sample_rows = sample_subann[sample_indexer]
    if len(this_sample_rows) == 0:
        _LOGGER.debug("No merge rows for sample '%s', skipping", sample.name)
        return merged_attrs
    _LOGGER.log(5, "%d rows to merge", len(this_sample_rows))
    _LOGGER.log(5, "Merge rows dict: {}".format(this_sample_rows.to_dict()))

    # For each row in the merge table of this sample:
    # 1) populate any derived columns
    # 2) derived columns --> space-delimited strings
    # 3) update the sample values with the merge table
    # Keep track of merged cols,
    # so we don't re-derive them later.
    merged_attrs = {key: "" for key in this_sample_rows.columns}
    subsamples = []
    _LOGGER.debug(this_sample_rows)
    for subsample_row_id, row in this_sample_rows.iterrows():
        try:
            row['subsample_name']
        except KeyError:
            # default to a numeric count on subsamples if they aren't named
            row['subsample_name'] = str(subsample_row_id)
        subann_unit = Subsample(row)
        subsamples.append(subann_unit)
        _LOGGER.debug(subsamples)
        rowdata = row.to_dict()

        # Iterate over column names to avoid Python3 RuntimeError for
        # during-iteration change of dictionary size.
        for attr_name in this_sample_rows.columns:
            if attr_name == sample_colname or \
                    attr_name not in derived_attributes:
                _LOGGER.log(5, "Skipping merger of attribute '%s'", attr_name)
                continue

            attr_value = rowdata[attr_name]

            # Initialize key in parent dict.
            col_key = attr_name + COL_KEY_SUFFIX
            merged_attrs[col_key] = ""
            rowdata[col_key] = attr_value
            data_src_path = sample.locate_data_source(
                data_sources, attr_name, source_key=rowdata[attr_name],
                extra_vars=rowdata)  # 1)
            rowdata[attr_name] = data_src_path

        _LOGGER.log(5, "Adding derived attributes")

        for attr in derived_attributes:

            # Skip over any attributes that the sample lacks or that are
            # covered by the data from the current (row's) data.
            if not hasattr(sample, attr) or attr in rowdata:
                _LOGGER.log(5, "Skipping column: '%s'", attr)
                continue

            # Map key to sample's value for the attribute given by column name.
            col_key = attr + COL_KEY_SUFFIX
            rowdata[col_key] = getattr(sample, attr)
            # Map the col/attr name itself to the populated data source 
            # template string.
            rowdata[attr] = sample.locate_data_source(
                data_sources, attr, source_key=getattr(sample, attr),
                extra_vars=rowdata)

        # TODO: this (below) is where we could maintain grouped values
        # TODO (cont.): as a collection and defer the true merger.

        # Since we are now jamming multiple (merged) entries into a single
        # attribute on a Sample, we have to join the individual items into a
        # space-delimited string and then use that value as the Sample
        # attribute. The intended use case for this sort of merge is for
        # multiple data source paths associated with a single Sample, hence
        # the choice of space-delimited string as the joined-/merged-entry
        # format--it's what's most amenable to use in building up an argument
        # string for a pipeline command.
        for attname, attval in rowdata.items():
            if attname == sample_colname or not attval:
                _LOGGER.log(5, "Skipping KV: {}={}".format(attname, attval))
                continue
            _LOGGER.log(5, "merge: sample '%s'; '%s'='%s'",
                        str(sample.name), str(attname), str(attval))
            if attname not in merged_attrs:
                new_attval = str(attval).rstrip()
            else:
                new_attval = "{} {}".format(merged_attrs[attname],
                                            str(attval)).strip()
            merged_attrs[attname] = new_attval  # 2)
            _LOGGER.log(5, "Stored '%s' as value for '%s' in merged_attrs",
                        new_attval, attname)

    # If present, remove sample name from the data with which to update sample.
    merged_attrs.pop(sample_colname, None)

    _LOGGER.log(5, "Updating Sample {}: {}".format(sample.name, merged_attrs))
    sample.update(merged_attrs)  # 3)
    sample.merged_cols = merged_attrs
    sample.merged = True
    sample.subsamples = subsamples

    return sample


@copy
class Paths(object):
    """ A class to hold paths as attributes. """

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self == other

    def __getitem__(self, key):
        return getattr(self, key)
    
    def __iter__(self):
        return iter(self.__dict__.values())
    
    def __repr__(self):
        return "Paths object."
