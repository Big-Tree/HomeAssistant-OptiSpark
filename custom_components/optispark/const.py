"""Constants for Optispark."""
from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

NAME = "Optispark"
DOMAIN = "optispark"
VERSION = "0.1.6"
ATTRIBUTION = "Data provided by http://jsonplaceholder.typicode.com/"

LAMBDA_TEMP = 'temps'
LAMBDA_PRICE = 'prices'
LAMBDA_OPTIMISED_DEMAND = 'optimised_demand'
LAMBDA_BASE_DEMAND = 'base_demand'
LAMBDA_BASE_COST = 'base_cost'
LAMBDA_OPTIMISED_COST = 'optimised_cost'
LAMBDA_PROJECTED_PERCENT_SAVINGS = 'projected_percent_savings'
# Lambda parameters
LAMBDA_SET_POINT = 'set_point'
LAMBDA_TEMP_RANGE = 'temp_range'
LAMBDA_POSTCODE = 'postcode'
LAMBDA_HOUSE_CONFIG = 'house_config'

HISTORY_DAYS = 3  # the number of days initially required by our algorithm
DYNAMO_HISTORY_DAYS = 365*5
MAX_UPLOAD_HISTORY_READINGS = 5000
DATABASE_COLUMN_SENSOR_HEAT_PUMP_POWER = 'heat_pump_power'
DATABASE_COLUMN_SENSOR_EXTERNAL_TEMPERATURE = 'external_temperature'
DATABASE_COLUMN_SENSOR_CLIMATE_ENTITY = 'climate_entity'

SWITCH_KEY = 'enable_optispark'
