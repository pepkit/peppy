"""auth exceptions"""


class PEPHubResponseException(Exception):
    """Request response exception. Used when response != 200."""

    def __init__(self, reason: str = ""):
        super(PEPHubResponseException, self).__init__(reason)


class PEPHubTokenExchangeException(Exception):
    """Exception in exchanging device code on token == 400."""

    def __init__(self, reason: str = ""):
        super(PEPHubTokenExchangeException, self).__init__(reason)
