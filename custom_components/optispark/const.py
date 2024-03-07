"""Constants for Optispark."""
from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

NAME = "Optispark"
DOMAIN = "optispark"
VERSION = "0.2.1"
ATTRIBUTION = "Data provided by http://jsonplaceholder.typicode.com/"

LAMBDA_TEMP = 'temps'
LAMBDA_TEMP_CONTROLS = 'temps'
LAMBDA_PRICE = 'prices'
LAMBDA_OPTIMISED_DEMAND = 'optimised_demand'
LAMBDA_BASE_DEMAND = 'base_demand'
LAMBDA_TIMESTAMP = 'timestamp'
LAMBDA_BASE_COST = 'base_cost'
LAMBDA_OPTIMISED_COST = 'optimised_cost'
LAMBDA_PROJECTED_PERCENT_SAVINGS = 'projected_percent_savings'
# Lambda parameters
LAMBDA_SET_POINT = 'temp_set_point'
LAMBDA_TEMP_RANGE = 'temp_range'
LAMBDA_POSTCODE = 'postcode'
LAMBDA_USER_HASH = 'user_hash'
LAMBDA_INITIAL_INTERNAL_TEMP = 'initial_internal_temp'
LAMBDA_OUTSIDE_RANGE = 'outside_range'

HISTORY_DAYS = 28  # the number of days initially required by our algorithm
DYNAMO_HISTORY_DAYS = 365*2
MAX_UPLOAD_HISTORY_READINGS = 5000
DATABASE_COLUMN_SENSOR_HEAT_PUMP_POWER = 'heat_pump_power'
DATABASE_COLUMN_SENSOR_EXTERNAL_TEMPERATURE = 'external_temperature'
DATABASE_COLUMN_SENSOR_CLIMATE_ENTITY = 'climate_entity'

SWITCH_KEY = 'enable_optispark'
