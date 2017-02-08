""" Exceptions for specific looper issues. """


class DefaultLooperenvException(Exception):
    """ Default looperenv setup call failed to
     set relevant `Project` attributes. """
    def __init__(self, reason):
        super(DefaultLooperenvException, self).__init__(reason)
