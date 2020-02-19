"""
Build a Project object.
"""
from .const import *
from .utils import copy, non_null_value
from .exceptions import *
from .sample2 import Sample2
from attmap import PathExAttMap
from ubiquerg import is_url
from collections import Mapping
import yaml
import warnings

from logging import getLogger

import pandas as pd
import os

READ_CSV_KWARGS = {"engine": "python", "dtype": str, "index_col": False,
                   "keep_default_na": False, "na_values": [""]}

_LOGGER = getLogger(PKG_NAME)


@copy
class Project2(PathExAttMap):
    """
    A class to model a Project (collection of samples and metadata).

    :param str | Mapping cfg: Project config file (YAML), or appropriate
        key-value mapping of data to constitute project
    :param str subproject: Subproject to use within configuration file, optional

    :Example:

    .. code-block:: python

        from models import Project
        prj = Project("config.yaml")

    """

    # Hook for Project's declaration of how it identifies samples.
    # Used for validation and for merge_sample (derived cols and such)
    SAMPLE_NAME_IDENTIFIER = SAMPLE_NAME_COLNAME

    DERIVED_ATTRIBUTES_DEFAULT = [DATA_SOURCE_COLNAME]

    def __init__(self, cfg, subproject=None):
        _LOGGER.debug("Creating {}{}".format(
            self.__class__.__name__, " from file {}".format(cfg)
            if cfg else ""))
        super(Project2, self).__init__()
        if isinstance(cfg, str):
            self.config_file = os.path.abspath(cfg)
            _LOGGER.debug("Parsing {} config file".
                          format(self.__class__.__name__))
            sections = self.parse_config_file(subproject)
        else:
            self.config_file = None
            sections = cfg.keys()
        self._sections = sections
        self._samples = self.load_samples()
        # self.modify_samples()

    def load_samples(self):
        self._read_sample_data()
        samples_list = []
        for _, r in self[SAMPLE_ANNOTATIONS_KEY].iterrows():
            samples_list.append(Sample2(r.dropna(), prj=self))
        return samples_list

    def parse_config_file(self, subproject=None):
        """
        Parse provided yaml config file and check required fields exist.

        :param str subproject: Name of subproject to activate, optional
        :raises KeyError: if config file lacks required section(s)
        """

        with open(self.config_file, 'r') as conf_file:
            config = yaml.safe_load(conf_file)

        assert isinstance(config, Mapping), \
            "Config file parse did not yield a Mapping; got {} ({})".\
            format(config, type(config))

        _LOGGER.debug("Raw config data: {}".format(config))

        # Parse yaml into the project's attributes.
        _LOGGER.debug("Adding attributes: {}".format(", ".join(config)))
        self.add_entries(config)

        # Overwrite any config entries with entries in the subproject.
        if subproject:
            if non_null_value(SUBPROJECTS_SECTION, config):
                _LOGGER.debug("Adding entries for subproject '{}'".
                              format(subproject))
                try:
                    subproj_updates = config[SUBPROJECTS_SECTION][subproject]
                except KeyError:
                    raise MissingSubprojectError(subproject,
                                                 config[SUBPROJECTS_SECTION])
                _LOGGER.debug("Updating with: {}".format(subproj_updates))
                self.add_entries(subproj_updates)
                self._subproject = subproject
                _LOGGER.info("Using subproject: '{}'".format(subproject))
            else:
                raise MissingSubprojectError(subproject)
        else:
            _LOGGER.debug("No subproject requested")

        self.setdefault(CONSTANTS_DECLARATION, {})

        # Ensure required absolute paths are present and absolute.
        for var in self.required_metadata:
            if var not in self.metadata:
                raise ValueError("Missing required metadata item: '{}'"
                                 .format(var))
            self[METADATA_KEY][var] = os.path.expandvars(self.metadata.get(var))

        _LOGGER.debug("Project metadata: {}".format(self.metadata))

        # All variables in METADATA_KEY should be relative to project config.
        try:
            relative_vars = self[METADATA_KEY]
        except KeyError as e:
            raise type(e)(e.message + "; " + METADATA_KEY + " is required.")
        for var in relative_vars.keys():
            relpath = relative_vars[var]
            if relpath is None:
                continue
            _LOGGER.debug("Ensuring absolute path for '{}'".format(var))
            # Parsed from YAML, so small space of possible datatypes.
            if isinstance(relpath, list):
                absolute = [self._ensure_absolute(maybe_relpath)
                            for maybe_relpath in relpath]
            else:
                absolute = self._ensure_absolute(relpath)
            _LOGGER.debug("Setting '{}' to '{}'".format(var, absolute))
            relative_vars[var] = absolute

        return set(config.keys())

    def modify_samples(self):
        self.attr_constants()
        self.attr_synonyms()
        self.attr_imply()
        self.attr_derive()

    def attr_imply(self):
        pass

    def attr_synonyms(self):
        pass

    def attr_constants(self):
        pass

    def attr_derive(self):
        pass

    def __repr__(self):
        """ Representation in interpreter. """
        if len(self) == 0:
            return "{}"
        msg = "Project ({})".format(self.config_file) \
            if self.config_file else "Project:"
        try:
            num_samples = len(self._samples)
        except (AttributeError, TypeError):
            _LOGGER.debug("No samples established on project")
            num_samples = 0
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            msg = "{}\nSections: {}".format(msg, ", ".join(self._sections))
        if num_samples > 0:
            msg = "{}\n{} samples".format(msg, num_samples)
            context = " (showing first {})".format(num_samples) \
                if num_samples < num_samples else ""
            msg = "{}{}".format(msg, context)
        subs = self.get(SUBPROJECTS_SECTION)
        return "{}\nSubprojects: {}".\
            format(msg, ", ".join(subs.keys())) if subs else msg

    def validate(self):
        """
        Prioritize project module import sample module, not vice-versa, but we
        still need to use some info about Project classes here.

        :return bool: whether the given object is an instance of a Project or
            Project subclass, or whether the given type is Project or a subtype
        """
        t = self if isinstance(self, type) else type(self)
        return PROJECT_TYPENAME == t.__name__ or PROJECT_TYPENAME in [
            parent.__name__ for parent in t.__bases__]

    @property
    def required_metadata(self):
        """
        Names of metadata fields that must be present for a valid project.

        Make a base project as unconstrained as possible by requiring no
        specific metadata attributes. It's likely that some common-sense
        requirements may arise in domain-specific client applications, in
        which case this can be redefined in a subclass.

        :return Iterable[str]: names of metadata fields required by a project
        """
        return []

    @property
    def samples(self):
        """
        Generic/base Sample instance for each of this Project's samples.

        :return Iterable[Sample]: Sample instance for each
            of this Project's samples
        """
        if self._samples:
            return self._samples
        if self.sample_table is None:
            _LOGGER.warning("No samples are defined")
            return []

    def _ensure_absolute(self, maybe_relpath):
        """ Ensure that a possibly relative path is absolute. """
        if not isinstance(maybe_relpath, str):
            raise TypeError(
                "Attempting to ensure non-text value is absolute path: {} ({})".
                    format(maybe_relpath, type(maybe_relpath)))
        _LOGGER.debug("Ensuring absolute: '{}'".format(maybe_relpath))
        if os.path.isabs(maybe_relpath) or is_url(maybe_relpath):
            _LOGGER.debug("Already absolute")
            return maybe_relpath
        # Maybe we have env vars that make the path absolute?
        expanded = os.path.expanduser(os.path.expandvars(maybe_relpath))
        _LOGGER.debug("Expanded: '{}'".format(expanded))
        if os.path.isabs(expanded):
            _LOGGER.debug("Expanded is absolute")
            return expanded
        _LOGGER.debug("Making non-absolute path '{}' be absolute".
                      format(maybe_relpath))

        # Set path to an absolute path, relative to project config.
        config_dirpath = os.path.dirname(self.config_file)
        _LOGGER.debug("config_dirpath: {}".format(config_dirpath))
        abs_path = os.path.join(config_dirpath, maybe_relpath)
        return abs_path

    def _read_sample_data(self):
        """
        Read the sample_table and subsample_table into dataframes
        and store in the object root
        """
        no_metadata_msg = "No " + METADATA_KEY + ".{} specified"
        st = self[METADATA_KEY][SAMPLE_ANNOTATIONS_KEY]
        try:
            sst = self[METADATA_KEY][SAMPLE_SUBANNOTATIONS_KEY]
        except KeyError:
            sst = None
            _LOGGER.warning(no_metadata_msg.format(SAMPLE_SUBANNOTATIONS_KEY))
        if st:
            self[SAMPLE_ANNOTATIONS_KEY] = \
                pd.read_csv(st, sep=infer_delimiter(st), **READ_CSV_KWARGS)
        else:
            _LOGGER.warning(no_metadata_msg.format(SAMPLE_ANNOTATIONS_KEY))
            if sst:
                self[SAMPLE_SUBANNOTATIONS_KEY] = \
                    pd.read_csv(sst, sep=infer_delimiter(sst),
                                **READ_CSV_KWARGS)


def infer_delimiter(filepath):
    """
    From extension infer delimiter used in a separated values file.

    :param str filepath: path to file about which to make inference
    :return str | NoneType: extension if inference succeeded; else null
    """
    ext = os.path.splitext(filepath)[1][1:].lower()
    return {"txt": "\t", "tsv": "\t", "csv": ","}.get(ext)


