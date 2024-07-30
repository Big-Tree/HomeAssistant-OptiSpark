__all__ = [
    "OptisparkApiClientError",
    "OptisparkApiClientTimeoutError",
    "OptisparkApiClientCommunicationError",
    "OptisparkApiClientAuthenticationError",
    "OptisparkApiClientLambdaError",
    "OptisparkApiClientPostcodeError",
    "OptisparkApiClientUnitError",
    "OptisparkApiClientLocationError"
]


class OptisparkApiClientError(Exception):
    """Exception to indicate a general API error."""


class OptisparkApiClientTimeoutError(OptisparkApiClientError):
    """Lamba probably took too long starting up."""


class OptisparkApiClientCommunicationError(OptisparkApiClientError):
    """Exception to indicate a communication error."""


class OptisparkApiClientAuthenticationError(OptisparkApiClientError):
    """Exception to indicate an authentication error."""


class OptisparkApiClientLambdaError(OptisparkApiClientError):
    """Exception to indicate lambda return an error."""


class OptisparkApiClientPostcodeError(OptisparkApiClientError):
    """Exception to indicate invalid postcode."""


class OptisparkApiClientUnitError(OptisparkApiClientError):
    """Exception to indicate unit error."""


class OptisparkApiClientLocationError(OptisparkApiClientError):
    """Exception to indicate an location error."""


class OptisparkApiClientDeviceError(OptisparkApiClientError):
    """Exception to indicate an location error."""


class OptisparkApiClientThermostatError(OptisparkApiClientError):
    """Exception to indicate an thermostat error."""
