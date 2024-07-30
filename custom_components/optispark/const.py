"""Constants for Optispark."""
from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

NAME = "Optispark"
DOMAIN = "optispark"
VERSION = "0.2.6"
ATTRIBUTION = "Data provided by http://jsonplaceholder.typicode.com/"

LAMBDA_TEMP_CONTROLS = 'temp_controls'
LAMBDA_PRICE = 'electricity_price'
LAMBDA_OPTIMISED_DEMAND = 'optimised_power'
LAMBDA_BASE_DEMAND = 'base_power'
LAMBDA_TIMESTAMP = 'timestamp'
LAMBDA_BASE_COST = 'base_cost'
LAMBDA_OPTIMISED_COST = 'optimised_cost'
LAMBDA_PROJECTED_PERCENT_SAVINGS = 'projected_percent_savings'
LAMBDA_HOME_ASSISTANT_VERSION = 'home_assistant_version'
# Lambda parameters
LAMBDA_SET_POINT = 'temp_set_point'
LAMBDA_TEMP_RANGE = 'temp_range'
LAMBDA_POSTCODE = 'postcode'
LAMBDA_ADDRESS = 'address'
LAMBDA_CITY = 'city'
LAMBDA_USER_HASH = 'user_hash'
LAMBDA_INITIAL_INTERNAL_TEMP = 'initial_internal_temp'
LAMBDA_OUTSIDE_RANGE = 'outside_range'
LAMBDA_HEAT_PUMP_MODE_RAW = 'heat_pump_mode_raw'
LAMBDA_TEMP_CHANGED = 'temp_changed'

HISTORY_DAYS = 28  # the number of days initially required by our algorithm
DYNAMO_HISTORY_DAYS = 365*2
MAX_UPLOAD_HISTORY_READINGS = 5000
DATABASE_COLUMN_SENSOR_HEAT_PUMP_POWER = 'heat_pump_power'
DATABASE_COLUMN_SENSOR_EXTERNAL_TEMPERATURE = 'external_temperature'
DATABASE_COLUMN_SENSOR_CLIMATE_ENTITY = 'climate_entity'

UPDATE_INTERVAL = 10
UPDATE_DEVICE_DATA_INTERVAL = 300

SWITCH_KEY = 'enable_optispark'

TARIFF_PRODUCT_CODE = "AGILE-FLEX-22-11-25"
TARIFF_CODE = "E-1R-AGILE-FLEX-22-11-25-A"

INTEGRATION_NAME = 'HomeAssistant'
