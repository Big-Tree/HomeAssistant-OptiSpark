"""Constants for Optispark."""
from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

NAME = "Optispark"
DOMAIN = "optispark"
VERSION = "0.0.0"
ATTRIBUTION = "Data provided by http://jsonplaceholder.typicode.com/"

LAMBDA_TEMP = 'temps'
LAMBDA_PRICE = 'prices'
LAMBDA_OPTIMISED_DEMAND = 'optimised_demand'
LAMBDA_BASE_DEMAND = 'base_demand'
# Lambda parameters
LAMBDA_SET_POINT = 'set_point'
LAMBDA_TEMP_RANGE = 'temp_range'
LAMBDA_POSTCODE = 'postcode'
LAMBDA_HOUSE_CONFIG = 'house_config'
