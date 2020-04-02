from collections import Mapping, OrderedDict
from string import Formatter
from logging import getLogger
from copy import copy as cp
import glob
import os

from ubiquerg import size
from attmap import PathExAttMap

from .const import *
from .utils import copy, grab_project_data
from .exceptions import InvalidSampleTableFileException

_LOGGER = getLogger(PKG_NAME)
SAMPLE_YAML_FILE_KEY = "yaml_file"
SAMPLE_YAML_EXT = ".yaml"


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
    def __init__(self, series, prj=None):

        super(Sample, self).__init__()

        data = OrderedDict(series)
        _LOGGER.debug("Sample data: {}".format(data))

        # Attach Project reference
        try:
            data_proj = data.pop(PRJ_REF)
        except (AttributeError, KeyError):
            data_proj = None

        self.add_entries(data)

        if data_proj and PRJ_REF not in self:
            self[PRJ_REF] = data_proj

        typefam = PathExAttMap
        if PRJ_REF in self and prj:
            _LOGGER.warning("Project data provided both in data and as separate"
                            " constructor argument; using direct argument")
        if prj:
            self[PRJ_REF] = prj
        if not self.get(PRJ_REF):
            # Force empty attmaps to null and ensure something's set.
            self[PRJ_REF] = None
            _LOGGER.debug("No project reference for sample")
        else:
            prefix = "Project reference on a sample must be an instance of {}".\
                format(typefam.__name__)
            if not isinstance(self[PRJ_REF], Mapping):
                raise TypeError(
                    prefix + "; got {}".format(type(self[PRJ_REF]).__name__))
        self._derived_cols_done = []
        self._attributes = list(series.keys())

    def get_sheet_dict(self):
        """
        Create a K-V pairs for items originally passed in via the sample sheet.
        This is useful for summarizing; it provides a representation of the
        sample that excludes things like config files and derived entries.

        :return OrderedDict: mapping from name to value for data elements
            originally provided via the sample sheet (i.e., the a map-like
            representation of the instance, excluding derived items)
        """
        return OrderedDict([[k, getattr(self, k)] for k in self._attributes])

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
        base = self.sample_name if type(self) is Sample else \
            "{}{}{}".format(self.sample_name, delimiter, type(self).__name__)
        return "{}{}".format(base, SAMPLE_YAML_EXT)

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
        import yaml
        if not path:
            if not subs_folder_path:
                raise ValueError(
                    "To represent {} on disk, provide a full path or a "
                    "path to a parent (submissions) folder".
                        format(self.__class__.__name__)
                )
            _LOGGER.debug("Creating filename for Sample: {}".
                          format(self[SAMPLE_NAME_ATTR]))
            filename = self.generate_filename(delimiter=delimiter)
            _LOGGER.debug("Filename: {}".format(filename))
            path = os.path.join(subs_folder_path, filename)
        _LOGGER.debug("Setting Sample filepath: {}".format(path))
        self[SAMPLE_YAML_FILE_KEY] = path

        def obj2dict(obj, name=None, to_skip=(SUBSAMPLE_DF_KEY, SAMPLE_DF_KEY)):
            """
            Build representation of object as a dict, recursively
            for all objects that might be attributes of self.
            :param object obj: what to serialize to write to YAML.
            :param str name: name of the object to represent.
            :param Iterable[str] to_skip: names of attributes to ignore.
            """
            from pandas import isnull, Series
            from collections import Mapping
            from attmap import AttMap
            if name:
                _LOGGER.log(5, "Converting to dict: {}".format(name))
            if name == PRJ_REF:
                _LOGGER.debug("Attempting to store Samples's project data")
                prj_data = grab_project_data(obj)
                _LOGGER.debug("Sample's project data: {}".format(prj_data))
                return {k: obj2dict(v, name=k) for k, v in prj_data.items()}
            if isinstance(obj, list):
                return [obj2dict(i) for i in obj]
            if isinstance(obj, AttMap):
                return {k: obj2dict(v, name=k) for k, v in obj.items()
                        if k not in to_skip and not k.startswith("_")}
            elif isinstance(obj, Mapping):
                return {k: obj2dict(v, name=k) for k, v in obj.items()
                        if k not in to_skip and not k.startswith("_")}
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

        _LOGGER.debug("Serializing: {}".format(self[SAMPLE_NAME_ATTR]))
        serial = obj2dict(self)

        dst = self[SAMPLE_YAML_FILE_KEY]
        with open(dst, 'w') as outfile:
            _LOGGER.debug("Generating YAML data for: {}".format(self[SAMPLE_NAME_ATTR]))
            try:
                yaml_data = yaml.safe_dump(serial, default_flow_style=False)
            except yaml.representer.RepresenterError:
                _LOGGER.error("SERIALIZED SAMPLE DATA: {}".format(serial))
                raise
            outfile.write(yaml_data)
        return dst

    def validate_inputs(self, schema):
        """
        Determine which of this Sample's required attributes/files are missing
        and calculate sizes of the inputs

        The names of the attributes that are required and/or deemed as inputs
        are sourced from the schema,more specifically from required_input_attrs
        and input_attrs sections in samples section

        :param dict schema: schema dict to validate against
        :return (type, str): hypothetical exception type along with message
            about what's missing; null and empty if nothing exceptional
            is detected
        """
        sample_schema_dict = schema["properties"]["samples"]["items"]
        _LOGGER.debug("sample_schema_dict: {}\n".format(sample_schema_dict))
        self.all_inputs = set()
        self.required_inputs = set()
        if INPUTS_ATTR_NAME in sample_schema_dict:
            self[INPUTS_ATTR_NAME] = sample_schema_dict[INPUTS_ATTR_NAME]
            self.all_inputs.update(self.get_attr_values(INPUTS_ATTR_NAME))
        if REQ_INPUTS_ATTR_NAME in sample_schema_dict:
            self[REQ_INPUTS_ATTR_NAME] = sample_schema_dict[REQ_INPUTS_ATTR_NAME]
            self.required_inputs = self.get_attr_values(REQ_INPUTS_ATTR_NAME)
            self.all_inputs.update(self.required_inputs)
        self.input_file_size = \
            sum([size(f, size_str=False) or 0.0
                 for f in self.all_inputs if f != ""])/(1024 ** 3)
        if REQ_INPUTS_ATTR_NAME not in self or not self.required_inputs:
            _LOGGER.debug("No required inputs")
            return None, "", ""
        missing_files = []
        for paths in self.required_inputs:
            paths = paths if isinstance(paths, list) else [paths]
            for path in paths:
                _LOGGER.debug("Checking if required input path exists: '{}'"
                              .format(path))
                if not os.path.exists(path):
                    _LOGGER.warning("Missing required input file: '{}'".
                                    format(path))
                    missing_files.append(path)
        if not missing_files:
            return None, "", ""
        else:
            reason_key = "Missing file(s)"
            reason_detail = ", ".join(missing_files)
            return IOError, reason_key, reason_detail

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

    def derive_attribute(self, data_sources, attr_name):
        """
        Uses the template path provided in the project config section
        "data_sources" to piece together an actual path by substituting
        variables (encoded by "{variable}"") with sample attributes.

        :param Mapping data_sources: mapping from key name (as a value in
            a cell of a tabular data structure) to, e.g., filepath
        :param str attr_name: Name of sample attribute
            (equivalently, sample sheet column) specifying a derived column.
        :return str: regex expansion of data source specified in configuration,
            with variable substitutions made
        :raises ValueError: if argument to data_sources parameter is null/empty
        """

        def _format_regex(regex, items):
            """
            Format derived source with object attributes

            :param str regex: string to format,
                e.g. {identifier}{file_id}_data.txt
            :param Iterable[Iterable[Iterable | str]] items: items to format
                the string with
            :raise InvalidSampleTableFileException: if after merging
                subannotations the lengths of multi-value attrs are not even
            :return Iterable | str: formatted regex string(s)
            """
            keys = [i[1] for i in Formatter().parse(regex) if i[1] is not None]
            if not keys:
                return [regex]
            attr_lens = [len(v) for k, v in items.items()
                         if (isinstance(v, list) and k in keys)]
            if not bool(attr_lens):
                return [regex.format(**items)]
            if len(set(attr_lens)) != 1:
                msg = "All attributes to format the {} ({}) have to be the " \
                      "same length, got: {}. Correct your {}".\
                    format(DERIVED_SOURCES_KEY, regex, attr_lens,
                           SUBSAMPLE_SHEET_KEY)
                raise InvalidSampleTableFileException(msg)
            vals = []
            for i in range(0, attr_lens[0]):
                items_cpy = cp(items)
                for k in keys:
                    if isinstance(items_cpy[k], list):
                        items_cpy[k] = items_cpy[k][i]
                vals.append(regex.format(**items_cpy))
            return vals

        def _glob_regex(patterns):
            """
            Perform unix style pathname pattern expansion for multiple patterns

            :param Iterable[str] patterns: patterns to expand
            :return str | Iterable[str]: expanded patterns
            """
            outputs = []
            for p in patterns:
                if '*' in p or '[' in p:
                    _LOGGER.debug("Pre-glob: {}".format(p))
                    val_globbed = sorted(glob.glob(p))
                    if not val_globbed:
                        _LOGGER.debug("No files match the glob: '{}'".format(p))
                    else:
                        p = val_globbed
                        _LOGGER.debug("Post-glob: {}".format(p))

                outputs.extend(p if isinstance(p, list) else [p])
            return outputs if len(outputs) > 1 else outputs[0]

        if not data_sources:
            return None
        sn = self[SAMPLE_NAME_ATTR] \
            if SAMPLE_NAME_ATTR in self else "this sample"
        try:
            source_key = getattr(self, attr_name)
        except AttributeError:
            reason = "'{attr}': to locate sample's derived attribute source, " \
                     "provide the name of a key from '{sources}' or ensure " \
                     "sample has attribute '{attr}'".\
                format(attr=attr_name, sources=DERIVED_SOURCES_KEY)
            raise AttributeError(reason)

        try:
            regex = data_sources[source_key]
            _LOGGER.debug("Data sources: {}".format(data_sources))
        except KeyError:
            _LOGGER.debug("{}: config lacks entry for {} key: "
                          "'{}' in column '{}'; known: {}".
                          format(sn, DERIVED_SOURCES_KEY, source_key, attr_name,
                                 data_sources.keys()))
            return ""
        deriv_exc_base = "In sample '{sn}' cannot correctly parse derived " \
                         "attribute source: {r}.".format(sn=sn, r=regex)
        try:
            vals = _format_regex(regex, dict(self.items()))
            _LOGGER.debug("Formatted regex: {}".format(vals))
        except KeyError as ke:
            _LOGGER.warning(deriv_exc_base + " Can't access {ke} attribute".
                            format(ke=str(ke)))
        except Exception as e:
            _LOGGER.warning(deriv_exc_base + " Exception type: {e}".
                            format(e=str(type(e).__name__)))
        else:
            return _glob_regex(vals)
        return None

    @property
    def project(self):
        """
        Get the project mapping

        :return peppy.Project: project object the sample was created from
        """
        return self[PRJ_REF]

    def __setattr__(self, key, value):
        self._try_touch_samples()
        super(Sample, self).__setattr__(key, value)

    def __delattr__(self, item):
        self._try_touch_samples()
        super(Sample, self).__delattr__(item)

    def __setitem__(self, key, value):
        self._try_touch_samples()
        super(Sample, self).__setitem__(key, value)

    # The __reduce__ function provides an interface for
    # correct object serialization with the pickle module.
    def __reduce__(self):
        return (
            self.__class__,
            (self.as_series(),),
            (None, {}),
            iter([]),
            iter({PRJ_REF: self[PRJ_REF]}.items())
        )

    def __str__(self, max_attr=10):
        """ Representation in interpreter. """
        if len(self) == 0:
            return ""
        head = "Sample '{}'".format(self[SAMPLE_NAME_ATTR])
        try:
            prj_cfg = self[PRJ_REF][CONFIG_FILE_KEY]
        except KeyError:
            pass
        else:
            head += " in Project ({})".format(prj_cfg)
        pub_attrs = {k: v for k, v in self.items() if not k.startswith("_")}
        maxlen = max(map(len, pub_attrs.keys())) + 2
        attrs = ""
        counter = 0
        for k, v in pub_attrs.items():
            attrs += "\n{}{}".\
                format((k + ":").ljust(maxlen),
                       v if not isinstance(v, list) else ", ".join(v))
            if counter == max_attr:
                attrs += "\n\n...".ljust(maxlen) + \
                         "(showing first {})".format(max_attr)
                break
            counter += 1
        return head + "\n" + attrs

    def _excl_from_eq(self, k):
        """ Exclude the Project reference from object comparison. """
        return k == PRJ_REF or super(Sample, self)._excl_from_eq(k)

    def _excl_from_repr(self, k, cls):
        """ Exclude the Project reference from representation. """
        return k == PRJ_REF or super(Sample, self)._excl_from_repr(k, cls)

    def _try_touch_samples(self):
        """
        Safely sets sample edited flag to true
        """
        try:
            self[PRJ_REF][SAMPLE_EDIT_FLAG_KEY] = True
        except (KeyError, AttributeError):
            pass
