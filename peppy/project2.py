"""
Build a Project object.
"""
import os
from .const2 import *
from .utils import copy, non_null_value
from .exceptions import *
from .sample2 import Sample2
from attmap import PathExAttMap
from ubiquerg import is_url
from yacman import load_yaml as _load_yaml


import jsonschema
import yaml
import warnings
import pandas as pd

from collections import Mapping
from logging import getLogger
from copy import deepcopy

_LOGGER = getLogger(PKG_NAME)


@copy
class Project2(PathExAttMap):
    """
    A class to model a Project (collection of samples and metadata).

    :param str | Mapping cfg: Project config file (YAML), or appropriate
        key-value mapping of data to constitute project
    :param Iterable[str] amendments: amendments to use within configuration file
    """
    def __init__(self, cfg=None, sample_table_index=None,
                 subsample_table_index=None, amendments=None):
        _LOGGER.debug("Creating {}{}".format(
            self.__class__.__name__,
            " from file {}".format(cfg) if cfg else "")
        )
        super(Project2, self).__init__()
        if isinstance(cfg, str):
            cfg_pth = os.path.abspath(cfg)
            self.parse_config_file(cfg_pth, amendments)
            self[CONFIG_FILE_KEY] = cfg_pth
        else:
            self[CONFIG_FILE_KEY] = None
        self._samples = self.load_samples()
        self.st_index = sample_table_index or "sample_name"
        self.sst_index = subsample_table_index or "subsample_name"
        self[ACTIVE_AMENDMENTS_KEY] = None
        self.modify_samples()
        self[SAMPLE_EDIT_FLAG_KEY] = False
        self._sample_table = self._get_table_from_samples(index=self.st_index)

    def _get_table_from_samples(self, index):
        """
        Generate a data frame from samples. Excludes private
        attrs (prepended with an underscore)

        :return pandas.DataFrame: a data frame with current samples attributes
        """
        df = pd.DataFrame()
        for sample in self.samples:
            sd = sample.to_dict()
            ser = pd.Series(
                {k: v for (k, v) in sd.items() if not k.startswith("_")}
            )
            df = df.append(ser, ignore_index=True)
        _LOGGER.debug("setting sample_table index to: {}".format(index))
        df.set_index(keys=index, drop=False)
        return df

    def parse_config_file(self, cfg_path, amendments=None):
        """
        Parse provided yaml config file and check required fields exist.

        :param str cfg_path: path to the config file to read and parse
        :param Iterable[str] amendments: Name of amendments to activate
        :raises KeyError: if config file lacks required section(s)
        """
        if CONFIG_KEY not in self:
            self[CONFIG_KEY] = PathExAttMap()
        with open(cfg_path, 'r') as conf_file:
            config = yaml.safe_load(conf_file)

        assert isinstance(config, Mapping), \
            "Config file parse did not yield a Mapping; got {} ({})".\
            format(config, type(config))

        _LOGGER.debug("Raw ({}) config data: {}".format(cfg_path, config))

        # recursively import configs
        if CFG_IMPORTS_KEY in config and config[CFG_IMPORTS_KEY]:
            _LOGGER.info("Importing external Project configurations: {}".
                         format(", ".join(config[CFG_IMPORTS_KEY])))
            for i in config[CFG_IMPORTS_KEY]:
                _LOGGER.debug("Processing external config: {}".format(i))
                if os.path.exists(i):
                    self.parse_config_file(cfg_path=i)
                else:
                    _LOGGER.warning("External Project configuration does not"
                                    " exist: {}".format(i))

        self[CONFIG_KEY].add_entries(config)
        # Parse yaml into the project's attributes.
        _LOGGER.debug("Adding attributes: {}".format(", ".join(config)))
        # Overwrite any config entries with entries in the amendments.
        amendments = [amendments] if isinstance(amendments, str) else amendments
        if amendments:
            for amendment in amendments:
                if non_null_value(AMENDMENTS_KEY, config):
                    _LOGGER.debug("Adding entries for amendment '{}'".
                                  format(amendment))
                    try:
                        amends = config[AMENDMENTS_KEY][amendment]
                    except KeyError:
                        raise MissingAmendmentError(amendment,
                                                     config[AMENDMENTS_KEY])
                    _LOGGER.debug("Updating with: {}".format(amends))
                    self[CONFIG_KEY].add_entries(amends)
                    _LOGGER.info("Using amendment: '{}'".format(amendment))
                else:
                    raise MissingAmendmentError(amendment)
            self[ACTIVE_AMENDMENTS_KEY] = amendments

        self[CONFIG_KEY][CONFIG_VERSION_KEY] = self._get_cfg_v()
        if self[CONFIG_KEY][CONFIG_VERSION_KEY] < 2:
            self._format_cfg()
        # here specify cfg sections that may need expansion
        relative_vars = [CFG_SAMPLE_TABLE_KEY, CFG_SUBSAMPLE_TABLE_KEY]
        self._make_sections_absolute(relative_vars, cfg_path)

    def _make_sections_absolute(self, sections, cfg_path):
        for key in sections:
            try:
                relpath = self[CONFIG_KEY][key]
            except KeyError:
                _LOGGER.debug("No '{}' section in configuration file: {}".
                              format(key, cfg_path))
                continue
            if relpath is None:
                continue
            _LOGGER.debug("Ensuring absolute path for '{}'".format(relpath))
            # Parsed from YAML, so small space of possible datatypes.
            if isinstance(relpath, list):
                absolute = [_ensure_path_absolute(maybe_relpath, cfg_path)
                            for maybe_relpath in relpath]
            else:
                absolute = _ensure_path_absolute(relpath, cfg_path)
            _LOGGER.debug("Setting '{}' to '{}'".format(key, absolute))
            self[CONFIG_KEY][key] = absolute

    def load_samples(self):
        self._read_sample_data()
        samples_list = []
        if SAMPLE_DF_KEY not in self:
            _LOGGER.warn("sample_table was not loaded, can't create Samples")
            return []
        for _, r in self[SAMPLE_DF_KEY].iterrows():
            samples_list.append(Sample2(r.dropna(), prj=self))
        return samples_list

    def modify_samples(self):
        if CONFIG_KEY not in self or MODIFIERS_KEY not in self[CONFIG_KEY]:
            return
        self.attr_constants()
        self.attr_synonyms()
        self.attr_imply()
        self._assert_samples_have_names()
        self.attr_merge()
        self.attr_derive()

    def attr_constants(self):
        """
        Update each Sample with constants declared by a Project.
        If Project does not declare constants, no update occurs.
        """
        if CONSTANT_KEY in self[CONFIG_KEY][MODIFIERS_KEY]:
            _LOGGER.debug("Applying constant attributes: {}".
                          format(self[CONFIG_KEY][MODIFIERS_KEY][CONSTANT_KEY]))
            [s.update(self[CONFIG_KEY][MODIFIERS_KEY][CONSTANT_KEY])
             for s in self.samples]

    def attr_synonyms(self):
        """
        Copy attribute values for all samples to a new one
        """
        if DUPLICATED_KEY in self[CONFIG_KEY][MODIFIERS_KEY]:
            synonyms = self[CONFIG_KEY][MODIFIERS_KEY][DUPLICATED_KEY]
            _LOGGER.debug("Applying synonyms: {}".format(synonyms))
            for sample in self.samples:
                for attr, new in synonyms.items():
                    if attr in sample:
                        setattr(sample, new, getattr(sample, attr))

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
            if SAMPLE_NAME_ATTR in self[CONFIG_KEY][MODIFIERS_KEY][DERIVED_KEY]:
                self.attr_derive(attrs=[SAMPLE_NAME_ATTR])
        except KeyError:
            pass
        for sample in self.samples:
            try:
                sample.sample_name
            except (KeyError, AttributeError):
                msg = "{st} is missing '{sn}' column;" \
                      " you must specify {sn}s in {st} or derive them".\
                    format(st=CFG_SAMPLE_TABLE_KEY, sn=SAMPLE_NAME_ATTR)
                raise InvalidSampleTableFileException(msg)

    def attr_merge(self):
        """
        Merge sample subannotations (from subsample table) with
        sample annotations (from sample_table)
        """
        if SUBSAMPLE_DF_KEY not in self or self[SUBSAMPLE_DF_KEY] is None:
            _LOGGER.debug("No {} found, skpping merge".
                          format(CFG_SUBSAMPLE_TABLE_KEY))
            return
        self._check_subann_name_overlap()
        merged_attrs = {}
        subsample_table = self[SUBSAMPLE_DF_KEY]
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
                    if attname == sample_colname or not attval:
                        _LOGGER.debug("Skipping KV: {}={}".
                                      format(attname, attval))
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
        try:
            implications = self[CONFIG_KEY][MODIFIERS_KEY][IMPLIED_KEY]
        except KeyError:
            return
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
        da = self[CONFIG_KEY][MODIFIERS_KEY][DERIVED_KEY]
        ds = self[CONFIG_KEY][MODIFIERS_KEY][DERIVED_SOURCES_KEY]
        derivations = attrs or (da if isinstance(da, list) else [da])
        _LOGGER.debug("Derivations to be done: {}".format(derivations))
        for sample in self.samples:
            for attr in derivations:
                if not hasattr(sample, attr):
                    _LOGGER.debug("sample lacks '{}' attribute".format(attr))
                    continue
                elif attr in sample._derived_cols_done:
                    _LOGGER.debug("'{}' has been derived".format(attr))
                    continue
                _LOGGER.debug("Deriving '{}' attribute for '{}'".
                              format(attr, sample.sample_name))

                # Set {atr}_key, so the original source can also be retrieved
                setattr(sample, ATTR_KEY_PREFIX + attr, getattr(sample, attr))

                derived_attr = sample.derive_attribute(ds, attr)
                if derived_attr:
                    _LOGGER.debug(
                        "Setting '{}' to '{}'".format(attr, derived_attr))
                    setattr(sample, attr, derived_attr)
                else:
                    _LOGGER.debug("Not setting null/empty value for data source"
                                  " '{}': {}".format(attr, type(derived_attr)))
                sample._derived_cols_done.append(attr)

    def activate_amendments(self, amendments):
        """
        Update settings based on amendment-specific values.

        This method will update Project attributes, adding new values
        associated with the amendments indicated, and in case of collision with
        an existing key/attribute the amendments' values will be favored.

        :param Iterable[str] amendments: A string with amendment
            names to be activated
        :return peppy.Project: Updated Project instance
        :raise TypeError: if argument to amendment parameter is null
        :raise NotImplementedError: if this call is made on a project not
            created from a config file
        """
        amendments = [amendments] if isinstance(amendments, str) else amendments
        if amendments is None:
            raise TypeError(
                "The amendment argument can not be null. To deactivate a "
                "amendment use the deactivate_amendments method.")
        if not self[CONFIG_FILE_KEY]:
            raise NotImplementedError(
                "amendment activation isn't supported on a project not "
                "created from a config file")
        prev = [(k, v) for k, v in self.items() if not k.startswith("_")]
        conf_file = self[CONFIG_FILE_KEY]
        self.__init__(conf_file, amendments)
        for k, v in prev:
            if k.startswith("_"):
                continue
            if k not in self or (self.is_null(k) and v is not None):
                _LOGGER.debug("Restoring {}: {}".format(k, v))
                self[k] = v
        self[ACTIVE_AMENDMENTS_KEY] = amendments
        return self

    def deactivate_amendments(self):
        """
        Bring the original project settings back.

        :return peppy.Project: Updated Project instance
        :raise NotImplementedError: if this call is made on a project not
            created from a config file
        """
        if self[ACTIVE_AMENDMENTS_KEY] is None:
            _LOGGER.warning("No amendments have been activated.")
            return self
        if not self[CONFIG_FILE_KEY]:
            raise NotImplementedError(
                "amendments deactivation isn't supported on a project that "
                "lacks a config file.")
        self.__init__(self[CONFIG_FILE_KEY])
        return self

    def add_samples(self, samples):
        """
        Add list of Sample objects

        :param peppy.Sample | Iterable[peppy.Sample] samples: samples to add
        """
        samples = [samples] if isinstance(samples, Sample2) else samples
        for sample in samples:
            if isinstance(sample, Sample2):
                self._samples.append(sample)
                self[SAMPLE_EDIT_FLAG_KEY] = True
            else:
                _LOGGER.warning("not a peppy.Sample object, not adding")

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

    def __str__(self):
        """ Representation in interpreter. """
        if len(self) == 0:
            return "{}"
        msg = "Project ({})".format(self[CONFIG_FILE_KEY]) \
            if self[CONFIG_FILE_KEY] else "Project:"
        try:
            num_samples = len(self._samples)
        except (AttributeError, TypeError):
            _LOGGER.debug("No samples established on project")
            num_samples = 0
        if num_samples > 0:
            msg = "{}\n{} samples".format(msg, num_samples)
            sample_names = list(self[SAMPLE_DF_KEY][SAMPLE_NAME_ATTR])
            repr_names = sample_names[:MAX_PROJECT_SAMPLES_REPR]
            context = " (showing first {})".format(MAX_PROJECT_SAMPLES_REPR) \
                if num_samples > MAX_PROJECT_SAMPLES_REPR else ""
            msg = "{}{}: {}".format(msg, context, ", ".join(repr_names))
        else:
            msg = "{} {}".format(msg, "no samples")
        if CONFIG_KEY not in self:
            return msg
        msg = "{}\nSections: {}".\
            format(msg, ", ".join([s for s in self[CONFIG_KEY].keys()]))
        if AMENDMENTS_KEY in self[CONFIG_KEY]:
            msg = "{}\nAmendments: {}".\
                format(msg, ", ".join(self[CONFIG_KEY][AMENDMENTS_KEY].keys()))
        if self[ACTIVE_AMENDMENTS_KEY]:
            msg = "{}\nActivated amendments: {}".\
                format(msg, ", ".join(self[ACTIVE_AMENDMENTS_KEY]))
        return msg

    @property
    def config(self):
        """
        Get the config mapping

        :return Mapping: config. May be formatted to comply with the most
            recent version specifications
        """
        return self[CONFIG_KEY]

    @property
    def config_file(self):
        """
        Get the config file path

        :return str: path to the config file
        """
        return self[CONFIG_FILE_KEY]

    @property
    def samples(self):
        """
        Generic/base Sample instance for each of this Project's samples.

        :return Iterable[Sample]: Sample instance for each
            of this Project's samples
        """
        if self._samples:
            return self._samples
        if SAMPLE_DF_KEY not in self or self[SAMPLE_DF_KEY] is None:
            _LOGGER.warning("No samples are defined")
            return []

    @property
    def amendments(self):
        """
        Return currently active list of amendments or None if none was activated

        :return Iterable[str]: a list of currently active amendment names
        """
        return self[ACTIVE_AMENDMENTS_KEY]

    @property
    def sample_table(self):
        """
        Get sample table. If any sample edits were performed,
        it will be re-generated

        :return pandas.DataFrame: a data frame with current samples attributes
        """
        if self[SAMPLE_EDIT_FLAG_KEY]:
            _LOGGER.debug("Generating new sample_table DataFrame")
            self[SAMPLE_EDIT_FLAG_KEY] = False
            return self._get_table_from_samples(index=self.st_index)
        _LOGGER.debug("Returning stashed sample_table DataFrame")
        return self._sample_table

    @property
    def subsample_table(self):
        """
        Get subsample table

        :return pandas.DataFrame: a data frame with subsample attributes
        """
        if isinstance(self[SUBSAMPLE_DF_KEY], pd.DataFrame):
            self[SUBSAMPLE_DF_KEY].set_index(keys=self.sst_index, drop=False)
        return self[SUBSAMPLE_DF_KEY]

    def _read_sample_data(self):
        """
        Read the sample_table and subsample_table into dataframes
        and store in the object root
        """
        read_csv_kwargs = {"engine": "python", "dtype": str, "index_col": False,
                           "keep_default_na": False, "na_values": [""]}
        no_metadata_msg = "No {} specified"
        if CONFIG_KEY not in self:
            _LOGGER.warn("No config key in Project")
            return
        st = self[CONFIG_KEY][CFG_SAMPLE_TABLE_KEY]
        try:
            sst = self[CONFIG_KEY][CFG_SUBSAMPLE_TABLE_KEY]
        except KeyError:
            sst = None
        if st:
            self[SAMPLE_DF_KEY] = \
                pd.read_csv(st, sep=infer_delimiter(st), **read_csv_kwargs)
        else:
            _LOGGER.warning(no_metadata_msg.format(CFG_SAMPLE_TABLE_KEY))
            self[SAMPLE_DF_KEY] = None
        if sst:
            self[SUBSAMPLE_DF_KEY] = \
                pd.read_csv(sst, sep=infer_delimiter(sst), **read_csv_kwargs)
        else:
            _LOGGER.debug(no_metadata_msg.format(CFG_SUBSAMPLE_TABLE_KEY))
            self[SUBSAMPLE_DF_KEY] = None

    def _get_cfg_v(self):
        """
        Get config file version number

        :raise InvalidConfigFileException: if new v2 section is used,
            but version==1 or no version is defined
        :return float: config version number
        """
        v = 1
        if CONFIG_VERSION_KEY in self[CONFIG_KEY]:
            v = self[CONFIG_KEY][CONFIG_VERSION_KEY]
            if not isinstance(v, (float, int)):
                raise InvalidConfigFileException("{} must be numeric".
                                                 format(CONFIG_VERSION_KEY))
        if MODIFIERS_KEY in self[CONFIG_KEY] and v < 2:
            raise InvalidConfigFileException(
                "Project configuration file ({p}) subscribes to {c} >= 2.0, "
                "since '{m}' section is defined. Set {c} to 2.0 in your config".
                    format(p=self[CONFIG_FILE_KEY], c=CONFIG_VERSION_KEY,
                           m=MODIFIERS_KEY))
        return float(v)

    def _format_cfg(self, mod_move_pairs=MODIFIERS_MOVE_PAIRS):
        """
        Format Project object to comply with the new config v2.0 specifications.
        All keys from metadata section will be moved to the root of config.
        mod_move_pairs will be used to move and rename sections
        to sample_modifiers section

        """
        def _mv_if_in(mapping, k_from=None, k_to=None, modifiers=False):
            """
            Move the sections within mapping

            :param Mapping mapping: object to move sections within
            :param str k_from: key of the section to move
            :param str k_to: key of the sample_modifiers subsection to move to
            """
            present = "Section '{}' already in '{}'"
            if modifiers:
                assert all(v is not None for v in [k_from, k_to]), \
                    "Keys can't be None"
                if k_from in mapping:
                    mapping.setdefault(MODIFIERS_KEY, PathExAttMap())
                    if k_to in mapping[MODIFIERS_KEY]:
                        _LOGGER.info(present.format(k_to,
                                                    mapping[MODIFIERS_KEY]))
                    else:
                        mapping[MODIFIERS_KEY][k_to] = mapping[k_from]
                        del mapping[k_from]
                        _LOGGER.debug("Section '{}' moved to: {}.{}".
                                      format(k_from, MODIFIERS_KEY, k_to))
            else:
                if METADATA_KEY in mapping:
                    for mk in mapping[METADATA_KEY].keys():
                        if mk in mapping:
                            _LOGGER.info(present.format(mk, mapping))
                        else:
                            mapping[mk] = mapping[METADATA_KEY][mk]
                            del mapping[METADATA_KEY][mk]
                            _LOGGER.debug("Section '{}.{}' moved to: {}".
                                          format(METADATA_KEY, mk, mk))
        for k, v in mod_move_pairs.items():
            _mv_if_in(self[CONFIG_KEY], k, v, modifiers=True)
        _mv_if_in(self[CONFIG_KEY], k, v)
        if METADATA_KEY in self[CONFIG_KEY]:
            del self[CONFIG_KEY][METADATA_KEY]

    def get_sample(self, sample_name):
        """
        Get an individual sample object from the project.

        Will raise a ValueError if the sample is not found.
        In the case of multiple samples with the same name (which is not
        typically allowed), a warning is raised and the first sample is returned

        :param str sample_name: The name of a sample to retrieve
        :return peppy.Sample: The requested Sample object
        """
        samples = self.get_samples([sample_name])
        if len(samples) > 1:
            _LOGGER.warning("More than one sample was detected; "
                            "returning the first")
        try:
            return samples[0]
        except IndexError:
            raise ValueError("Project has no sample named {}."
                             .format(sample_name))

    def get_samples(self, sample_names):
        """
        Returns a list of sample objects given a list of sample names

        :param list sample_names: A list of sample names to retrieve
        :return list[peppy.Sample]: A list of Sample objects
        """
        return [s for s in self.samples if s[SAMPLE_NAME_ATTR] in sample_names]

    def validate_project(self, schema, exclude_case=False):
        """
        Validate a project object against a schema

        :param str | dict schema: schema dict to validate against
            or a path to one
        :param bool exclude_case: whether to exclude validated objects
            from the error.
            Useful when used ith large projects
        """
        schema_dict = _read_schema(schema=schema)
        project_dict = self.to_dict()
        _validate_object(project_dict, _preprocess_schema(schema_dict),
                         exclude_case)
        _LOGGER.debug("Project validation successful")

    def validate_sample(self, sample_name, schema, exclude_case=False):
        """
        Validate the selected sample object against a schema

        :param str | int sample_name: name or index of the sample to validate
        :param str | dict schema: schema dict to validate against
            or a path to one
        :param bool exclude_case: whether to exclude validated objects
            from the error.
            Useful when used ith large projects
        """
        schema_dict = _read_schema(schema=schema)
        sample_dict = self.samples[sample_name] if isinstance(sample_name, int)\
            else self.get_sample(sample_name)
        sample_schema_dict = schema_dict["properties"]["samples"]["items"]
        _validate_object(sample_dict, sample_schema_dict, exclude_case)
        _LOGGER.debug("'{}' sample validation successful".format(sample_name))

    def validate_config(self, schema, exclude_case=False):
        """
        Validate the config part of the Project object against a schema

        :param str | dict schema: schema dict to validate against
            or a path to one
        :param bool exclude_case: whether to exclude validated objects
            from the error.
            Useful when used ith large projects
        """
        schema_dict = _read_schema(schema=schema)
        schema_cpy = deepcopy(schema_dict)
        try:
            del schema_cpy["properties"]["samples"]
        except KeyError:
            pass
        if "required" in schema_cpy:
            try:
                schema_cpy["required"].remove("samples")
            except ValueError:
                pass
        project_dict = self.to_dict()
        _validate_object(project_dict, schema_cpy, exclude_case)
        _LOGGER.debug("Config validation successful")

    def _check_subann_name_overlap(self):
        """
        Check if all subannotations have a matching sample, and warn if not
        """
        subsample_names = list(self[SUBSAMPLE_DF_KEY][SAMPLE_NAME_ATTR])
        sample_names_list = [s[SAMPLE_NAME_ATTR] for s in self.samples]
        for n in subsample_names:
            if n not in sample_names_list:
                _LOGGER.warning(("Couldn't find matching sample for "
                                 "subsample: {}").format(n))


def _validate_object(object, schema, exclude_case=False):
    """
    Generic function to validate object against a schema

    :param Mapping object: an object to validate
    :param str | dict schema: schema dict to validate against or a path to one
    :param bool exclude_case: whether to exclude validated objects
        from the error. Useful when used with large projects
    """
    try:
        jsonschema.validate(object, schema)
    except jsonschema.exceptions.ValidationError as e:
        if not exclude_case:
            raise
        raise jsonschema.exceptions.ValidationError(e.message)


def _read_schema(schema):
    """
    Safely read schema from YAML-formatted file.

    :param str | Mapping schema: path to the schema file
        or schema in a dict form
    :return dict: read schema
    :raise TypeError: if the schema arg is neither a Mapping nor a file path
    """
    if isinstance(schema, str):
        return _load_yaml(schema)
    elif isinstance(schema, dict):
        return schema
    raise TypeError("schema has to be either a dict, URL to remote schema "
                    "or a path to an existing file")


def _preprocess_schema(schema_dict):
    """
    Preprocess schema before validation for user's convenience
    Preprocessing includes: renaming 'samples' to '_samples'
    since in the peppy.Project object _samples attribute holds the list
    of peppy.Samples objects.

    :param dict schema_dict: schema dictionary to preprocess
    :return dict: preprocessed schema
    """
    _LOGGER.debug("schema ori: {}".format(schema_dict))
    if "samples" in schema_dict["properties"]:
        schema_dict["properties"]["_samples"] = \
            schema_dict["properties"]["samples"]
        del schema_dict["properties"]["samples"]
        schema_dict["required"][schema_dict["required"].index("samples")] = \
            "_samples"
    _LOGGER.debug("schema edited: {}".format(schema_dict))
    return schema_dict


def _ensure_path_absolute(maybe_relpath, cfg_path):
    """ Ensure that a possibly relative path is absolute. """
    if not isinstance(maybe_relpath, str):
        raise TypeError(
            "Attempting to ensure non-text value is absolute path: {} ({})".
                format(maybe_relpath, type(maybe_relpath)))
    if os.path.isabs(maybe_relpath) or is_url(maybe_relpath):
        _LOGGER.debug("Already absolute")
        return maybe_relpath
    # Maybe we have env vars that make the path absolute?
    expanded = os.path.expanduser(os.path.expandvars(maybe_relpath))
    if os.path.isabs(expanded):
        _LOGGER.debug("Expanded: {}".format(expanded))
        return expanded
    # Set path to an absolute path, relative to project config.
    config_dirpath = os.path.dirname(cfg_path)
    _LOGGER.debug("config_dirpath: {}".format(config_dirpath))
    abs_path = os.path.join(config_dirpath, maybe_relpath)
    _LOGGER.debug("Expanded and/or made absolute: {}".format(abs_path))
    return abs_path


def infer_delimiter(filepath):
    """
    From extension infer delimiter used in a separated values file.

    :param str filepath: path to file about which to make inference
    :return str | NoneType: extension if inference succeeded; else null
    """
    ext = os.path.splitext(filepath)[1][1:].lower()
    return {"txt": "\t", "tsv": "\t", "csv": ","}.get(ext)
