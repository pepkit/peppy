""" Looper versions of NGS project models. """

from . import models


__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"



class Project(models.Project):
    """
    Looper-specific NGS Project.

    :param config_file: path to configuration file with data from
        which Project is to be built
    :type config_file: str
    :param subproject: name indicating subproject to use, optional
    :type subproject: str
    :param default_compute: path to default compute environment
        configuration data, optional
    :type default_compute: str

    """
    def __init__(self, config_file, subproject=None, **kwargs):
        super(Project, self).__init__(
                config_file, subproject=subproject, 
                no_environment_exception=RuntimeError,
                no_compute_exception=RuntimeError, **kwargs)


    @property
    def required_metadata(self):
        """ Which metadata attributes are required. """
        return ["output_dir"]


    @property
    def project_folders(self):
        """ Keys for paths to folders to ensure exist. """
        return ["output_dir", "results_subdir", "submission_subdir"]


    @staticmethod
    def infer_name(path_config_file):
        """
        Infer project name from config file path.
        
        The assumption is that the config file lives in a 'metadata' subfolder 
        within a folder with a name representative of the project.
        
        :param str path_config_file: path to the project's config file.
        :return str: inferred name for project.
        """
        import os
        metadata_folder_path = os.path.dirname(path_config_file)
        proj_root_path, _ = os.path.split(metadata_folder_path)
        _, proj_root_name = os.path.split(proj_root_path)
        return proj_root_name
