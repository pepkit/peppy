""" Exceptions for specific looper issues. """


__author__ = "Vince Reuter"
__email__ = "vreuter@virginia.edu"


class ModelConstructionException(Exception):
    """ Error during construction of a looper ADT instance. """

    def __init__(self, datatype, stage="", context=""):
        """
        Explain failure during creation of `datatype` instance, with
        coarse contextual information given by `stage` and fine context
        given by `context`.

        :param str | type datatype: name of ADT under construction at
            time of error, or the type itself
        :param str stage: stage of the construction, optional
        :param str context: contextual information within stage, optional
        """
        filler = "unspecified"
        if isinstance(datatype, str):
            typename = datatype
        else:
            try:
                typename = datatype.__name__
            except AttributeError:
                typename = str(datatype)
        explanation = "Error creating {dt}; stage: {s}; context: {c}".\
            format(dt=typename, s=stage or filler, c=context or filler)
        super(ModelConstructionException, self).__init__(explanation)



class PipelinesException(Exception):
    """ Oh no, no pipelines for a project. """
    def __init__(self):
        super(PipelinesException, self).__init__()



class ProjectConstructionException(ModelConstructionException):
    """ An error occurred during attempt to instantiate `Project`. """

    def __init__(self, reason, stage=""):
        """
        Explain exception during `looper` `Project` construction.

        :param str reason: fine-grained contextual information
        :param str stage: broad phase of construction during which the
            error occurred
        """
        super(ProjectConstructionException, self).__init__(
            datatype="Project", stage=stage, context=reason)
