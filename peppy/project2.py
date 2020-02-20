"""
Build a Project object.
"""
from .const2 import *
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

_LOGGER = getLogger(PKG_NAME)


@copy
class Project2(PathExAttMap):
    """
    A class to model a Project (collection of samples and metadata).

    :param str | Mapping cfg: Project config file (YAML), or appropriate
        key-value mapping of data to constitute project
    :param str subproject: Subproject to use within configuration file, optional
    """
    def __init__(self, cfg, subproject=None):
        _LOGGER.debug("Creating {}{}".format(
            self.__class__.__name__, " from file {}".format(cfg)
            if cfg else ""))
        super(Project2, self).__init__()
        if isinstance(cfg, str):
            self[CONFIG_FILE_KEY] = os.path.abspath(cfg)
            self.parse_config_file(subproject)
        else:
            self[CONFIG_FILE_KEY] = None
        self._samples = self.load_samples()
        self.modify_samples()

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
        self[CONFIG_VERSION_KEY] = self._get_cfg_v()
        if self[CONFIG_VERSION_KEY] < 2:
            self._format_cfg()
        self["_config"] = self.to_dict()
        # Overwrite any config entries with entries in the subproject.
        if subproject:
            if non_null_value(SUBPROJECTS_KEY, config):
                _LOGGER.debug("Adding entries for subproject '{}'".
                              format(subproject))
                try:
                    subproj_updates = config[SUBPROJECTS_KEY][subproject]
                except KeyError:
                    raise MissingSubprojectError(subproject,
                                                 config[SUBPROJECTS_KEY])
                _LOGGER.debug("Updating with: {}".format(subproj_updates))
                self.add_entries(subproj_updates)
                self._subproject = subproject
                _LOGGER.info("Using subproject: '{}'".format(subproject))
            else:
                raise MissingSubprojectError(subproject)
        else:
            _LOGGER.debug("No subproject requested")

        # All variables in METADATA_KEY should be relative to project config.
        relative_vars = [SAMPLE_TABLE_KEY, SUBSAMPLE_TABLE_KEY]
        for key in relative_vars:
            relpath = self[key]
            if relpath is None:
                continue
            _LOGGER.debug("Ensuring absolute path for '{}'".format(relpath))
            # Parsed from YAML, so small space of possible datatypes.
            if isinstance(relpath, list):
                absolute = [self._ensure_absolute(maybe_relpath)
                            for maybe_relpath in relpath]
            else:
                absolute = self._ensure_absolute(relpath)
            _LOGGER.debug("Setting '{}' to '{}'".format(key, absolute))
            self[key] = absolute

    def load_samples(self):
        self._read_sample_data()
        samples_list = []
        for _, r in self[SAMPLE_TABLE_KEY].iterrows():
            samples_list.append(Sample2(r.dropna(), prj=self))
        return samples_list

    def modify_samples(self):
        self.attr_constants()
        # self.attr_synonyms()
        self.attr_imply()
        self._assert_samples_have_names()
        self.attr_merge()
        self.attr_derive()

    def attr_constants(self):
        """
        Update each Sample with constants declared by a Project.
        If Project does not declare constants, no update occurs.
        """
        if CONSTANTS_KEY in self:
            [s.update(self[MODIFIERS_KEY][CONSTANTS_KEY]) for s in self.samples]

    def attr_synonyms(self):
        pass

    def _assert_samples_have_names(self):
        """
        Make sure samples have sample_name attribute specified.
        Try to derive this attribute first.

        :raise InvalidSampleTableFileException: if names are not specified
        """
        try:
            # before merging, which is requires sample_name attribute to map
            # sample_table rows to subsample_table rows,
            # perform only sample_name attr derivation
            if SAMPLE_NAME_ATTR in self[MODIFIERS_KEY][DERIVED_KEY]:
                self.attr_derive(attrs=[SAMPLE_NAME_ATTR])
        except KeyError:
            pass
        for sample in self.samples:
            try:
                sample.sample_name
            except KeyError:
                msg = "{st} is missing '{sn}' column;" \
                      " you must specify {sn}s in {st} or derive them".\
                    format(st=SAMPLE_TABLE_KEY, sn=SAMPLE_NAME_ATTR)
                raise InvalidSampleTableFileException(msg)

    def attr_merge(self):
        """

        :return:
        """
        if SUBSAMPLE_TABLE_KEY not in self:
            _LOGGER.debug("No {} found, skpping merge".
                          format(SUBSAMPLE_TABLE_KEY))
            return
        merged_attrs = {}
        subsample_table = self[SUBSAMPLE_TABLE_KEY]
        for sample in self.samples:
            sample_colname = SAMPLE_NAME_ATTR
            if sample_colname not in subsample_table.columns:
                raise KeyError("Subannotation requires column '{}'."
                               .format(sample_colname))
            _LOGGER.debug("Using '{}' as sample name column from "
                          "subannotation table".format(sample_colname))
            sample_indexer = \
                subsample_table[sample_colname] == sample[SAMPLE_NAME_ATTR]
            this_sample_rows = subsample_table[sample_indexer].\
                dropna(how="any", axis=1)
            if len(this_sample_rows) == 0:
                _LOGGER.debug("No merge rows for sample '%s', skipping",
                              sample[SAMPLE_NAME_ATTR])
                return merged_attrs
            _LOGGER.debug("%d rows to merge", len(this_sample_rows))
            _LOGGER.debug("Merge rows dict: "
                          "{}".format(this_sample_rows.to_dict()))

            merged_attrs = {key: list() for key in this_sample_rows.columns}
            _LOGGER.debug(this_sample_rows)
            for subsample_row_id, row in this_sample_rows.iterrows():
                try:
                    row['subsample_name']
                except KeyError:
                    row['subsample_name'] = str(subsample_row_id)
                rowdata = row.to_dict()

                def _select_new_attval(merged_attrs, attname, attval):
                    """ Select new attribute value for the merged columns
                    dictionary """
                    if attname in merged_attrs:
                        return merged_attrs[attname] + [attval]
                    return [str(attval).rstrip()]

                for attname, attval in rowdata.items():
                    _LOGGER.debug("attname: {}".format(attname))
                    if attname == sample_colname or not attval:
                        _LOGGER.debug("Skipping KV: {}={}".format(attname, attval))
                        continue
                    _LOGGER.debug("merge: sample '{}'; "
                                  "'{}'='{}'".format(sample[SAMPLE_NAME_ATTR],
                                                     attname, attval))
                    merged_attrs[attname] = _select_new_attval(merged_attrs,
                                                               attname, attval)

            # If present, remove sample name from the data with which to update
            # sample.
            merged_attrs.pop(sample_colname, None)

            _LOGGER.debug("Updating Sample {}: {}".
                          format(sample[SAMPLE_NAME_ATTR], merged_attrs))
            sample.update(merged_attrs)

    def attr_imply(self):
        """
        Infer value for additional field(s) from other field(s).

        Add columns/fields to the sample based on values in those already-set
        that the sample's project defines as indicative of implications for
        additional data elements for the sample.
        """
        implications = self[MODIFIERS_KEY][IMPLIED_KEY]
        _LOGGER.debug("Sample attribute implications: {}".format(implications))
        if not implications:
            return
        for sample in self.samples:
            sn = sample[SAMPLE_NAME_ATTR] \
                if SAMPLE_NAME_ATTR in sample else "this sample"
            for implier_name, implied in implications.items():
                _LOGGER.debug("Setting Sample variable(s) implied by '{}'"
                              .format(implier_name))
                try:
                    implier_value = sample[implier_name]
                except KeyError:
                    _LOGGER.debug("No '{}' for {}".format(implier_name, sn))
                    continue
                try:
                    implied_val_by_attr = implied[implier_value]
                    _LOGGER.debug("Implications for '{}'='{}': {}".
                                  format(implier_name, implier_value,
                                         str(implied_val_by_attr)))
                    for colname, implied_value in implied_val_by_attr.items():
                        _LOGGER.debug("Setting '{}' attribute value to '{}'".
                                      format(colname, implied_value))
                        sample.__setitem__(colname, implied_value)
                except KeyError:
                    _LOGGER.debug("Unknown implied value for implier '{}'='{}'"
                                  .format(implier_name, implier_value))

    def attr_derive(self, attrs=None):
        """
        Set derived attributes for all Samples tied to this Project instance
        """
        da = self[MODIFIERS_KEY][DERIVED_KEY]
        ds = self[MODIFIERS_KEY][DERIVED_SOURCES_KEY]
        derivations = attrs or (da if isinstance(da, list) else [da])
        _LOGGER.debug("Derivations to be done: {}".format(derivations))
        for sample in self.samples:
            for attr in derivations:
                # Only proceed if the specified column exists
                # and was not already merged or derived.
                if not hasattr(sample, attr):
                    _LOGGER.debug("'{}' lacks '{}' attribute".
                                  format(sample.sample_name, attr))
                    continue
                elif attr in sample._derived_cols_done:
                    _LOGGER.debug("'{}' has been derived".format(attr))
                    continue
                _LOGGER.debug("Deriving '{}' attribute for '{}'".
                              format(attr, sample.sample_name))

                derived_attr = sample.derive_attribute(ds, attr)
                if derived_attr:
                    _LOGGER.debug(
                        "Setting '{}' to '{}'".format(attr, derived_attr))
                    setattr(sample, attr, derived_attr)

                else:
                    _LOGGER.debug(
                        "Not setting null/empty value for data source "
                        "'{}': {}".format(attr, type(derived_attr)))
                sample._derived_cols_done.append(attr)

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
            sections = [s for s in self.keys() if not s.startswith("_")]
            msg = "{}\nSections: {}".format(msg, ", ".join(sections))
        if num_samples > 0:
            msg = "{}\n{} samples".format(msg, num_samples)
            context = " (showing first {})".format(num_samples) \
                if num_samples < num_samples else ""
            msg = "{}{}".format(msg, context)
        subs = self.get(SUBPROJECTS_KEY)
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
    def config(self):
        """
        Get the config mapping

        :return Mapping: config. May be formatted to comply with the most
            recent version specifications
        """
        return self._config

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
        read_csv_kwargs = {"engine": "python", "dtype": str, "index_col": False,
                           "keep_default_na": False, "na_values": [""]}
        no_metadata_msg = "No " + METADATA_KEY + ".{} specified"
        st = self[SAMPLE_TABLE_KEY]
        try:
            sst = self[SUBSAMPLE_TABLE_KEY]
        except KeyError:
            sst = None
            _LOGGER.warning(no_metadata_msg.format(SUBSAMPLE_TABLE_KEY))
        if st:
            self[SAMPLE_TABLE_KEY] = \
                pd.read_csv(st, sep=infer_delimiter(st), **read_csv_kwargs)
        else:
            _LOGGER.warning(no_metadata_msg.format(SAMPLE_TABLE_KEY))
        if sst:
            self[SUBSAMPLE_TABLE_KEY] = \
                pd.read_csv(sst, sep=infer_delimiter(sst), **read_csv_kwargs)
        else:
            _LOGGER.debug(no_metadata_msg.format(SUBSAMPLE_TABLE_KEY))

    def _get_cfg_v(self):
        """
        Get config file version number

        :raise InvalidConfigFileException: if new v2 section is used,
            but version==1 or no version is defined
        :return float: config version number
        """
        v = 1
        if CONFIG_VERSION_KEY in self:
            v = self[CONFIG_VERSION_KEY]
            if not isinstance(v, (float, int)):
                raise InvalidConfigFileException("{} must be numeric".
                                                 format(CONFIG_VERSION_KEY))
        if MODIFIERS_KEY in self and v < 2:
            raise InvalidConfigFileException(
                "Project configuration file ({p}) subscribes to {c} >= 2.0, "
                "since '{m}' section is defined. Set {c} to 2.0 in your config".
                    format(p=self[CONFIG_FILE_KEY], c=CONFIG_VERSION_KEY,
                           m=MODIFIERS_KEY))
        return float(v)

    def _format_cfg(self):
        """
        Format Project object to comply with the new config v2.0 specifications
        """
        mod_move_pairs = {
            "derived_attributes": DERIVED_KEY,
            "derived_columns": DERIVED_KEY,
            "constant_attributes": CONSTANTS_KEY,
            "implied_attributes": IMPLIED_KEY,
            "implied_columns": IMPLIED_KEY,
            "data_sources": DERIVED_SOURCES_KEY
        }

        metadata_move_pairs = {
            SAMPLE_TABLE_KEY: SAMPLE_TABLE_KEY,
            SUBSAMPLE_TABLE_KEY: SUBSAMPLE_TABLE_KEY,
            "sample_annotation": SAMPLE_TABLE_KEY,
            "sample_subannotation": SUBSAMPLE_TABLE_KEY
        }

        def _mv_if_in(mapping, k_from, k_to, modifiers=False):
            """
            Move the sections within mapping

            :param Mapping mapping: object to move sections within
            :param str k_from: key of the section to move
            :param str k_to: key of the sample_modifiers subsection to move to
            """
            if modifiers:
                if k_from in mapping:
                    mapping.setdefault(MODIFIERS_KEY, PathExAttMap())
                    mapping[MODIFIERS_KEY][k_to] = mapping[k_from]
                    del mapping[k_from]
                    _LOGGER.debug("Section '{}' moved to: {}.{}".
                                  format(k_from, MODIFIERS_KEY, k_to))
            else:
                if METADATA_KEY in mapping and k_from in mapping[METADATA_KEY]:
                    mapping[k_to] = mapping[METADATA_KEY][k_from]
                    del mapping[METADATA_KEY][k_from]
                    _LOGGER.debug("Section '{}.{}' moved to: {}".
                                  format(METADATA_KEY, k_from, k_to))
        for k, v in mod_move_pairs.items():
            _mv_if_in(self, k, v, modifiers=True)
        for k, v in metadata_move_pairs.items():
            _mv_if_in(self, k, v)
        if not self[METADATA_KEY]:
            del self[METADATA_KEY]


def infer_delimiter(filepath):
    """
    From extension infer delimiter used in a separated values file.

    :param str filepath: path to file about which to make inference
    :return str | NoneType: extension if inference succeeded; else null
    """
    ext = os.path.splitext(filepath)[1][1:].lower()
    return {"txt": "\t", "tsv": "\t", "csv": ","}.get(ext)


