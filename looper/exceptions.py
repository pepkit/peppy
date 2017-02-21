""" Exceptions for specific looper issues. """


# Simplify imports by permitting '*', especially for models.
__all__ = ["ComputeEstablishmentException", "DefaultLooperenvException",
           "LooperConstructionException", "MetadataOperationException",
           "ProjectConstructionException"]


class MetadataOperationException(Exception):
    """ Illegal/unsupported operation, motivated by `AttributeDict`. """
    def __init__(self, obj, meta_item):
        """
        Instance with which the access attempt was made, along with the
        name of the reserved/privileged metadata item, define the exception.

        :param object obj: instance with which
            offending operation was attempted
        :param str meta_item: name of the reserved metadata item
        """
        try:
            classname = obj.__class__.__name__
        except AttributeError:
            # Maybe we were given a class or function not an instance?
            classname = obj.__name__
        explanation = "Attempted unsupported operation on {} item '{}'". \
            format(classname, meta_item)
        super(MetadataOperationException, self). \
            __init__(explanation)


class LooperConstructionException(Exception):
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
        super(LooperConstructionException, self).__init__(explanation)


class ProjectConstructionException(LooperConstructionException):
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


class DefaultLooperenvException(ProjectConstructionException):
    """ Default looperenv setup call failed to
     set relevant `Project` attributes. """
    def __init__(self, reason="Could not establish default looperenv"):
        super(DefaultLooperenvException, self).__init__(reason=reason)


class ComputeEstablishmentException(ProjectConstructionException):
    """ Failure to establish `Project` `compute` setting(s). """
    def __init__(self, reason="Could not establish Project compute env."):
        super(ComputeEstablishmentException, self).__init__(reason=reason)
