<<<<<<< HEAD
"""Constants for the Plate Recognizer integration."""

DOMAIN = "platerecognizer"

# API
API_URL_CLOUD = "https://api.platerecognizer.com/v1/plate-reader/"
API_URL_STATISTICS = "https://api.platerecognizer.com/v1/statistics/"

# Config entry keys
CONF_API_TOKEN = "api_token"
CONF_CAMERA_ENTITY = "camera_entity"
CONF_REGIONS = "regions"
CONF_WATCHED_PLATES = "watched_plates"
CONF_SAVE_FILE_FOLDER = "save_file_folder"
CONF_SAVE_TIMESTAMPED = "save_timestamped_file"
CONF_ALWAYS_SAVE_LATEST = "always_save_latest_file"
CONF_MMC = "mmc"
CONF_DETECTION_RULE = "detection_rule"
CONF_REGION_MODE = "region_mode"
CONF_SERVER = "server"
CONF_ON_PREMISE = "on_premise"

# Defaults
DEFAULT_MMC = False
DEFAULT_DETECTION_RULE = "none"
DEFAULT_REGION_MODE = "none"
DEFAULT_ON_PREMISE = False
DEFAULT_SERVER = "http://localhost:8080"
DEFAULT_SAVE_TIMESTAMPED = False
DEFAULT_ALWAYS_SAVE_LATEST = False

# Options
DETECTION_RULES = ["none", "strict"]
REGION_MODES = ["none", "strict"]

# Events — dot notation matches original integration
EVENT_VEHICLE_DETECTED = "platerecognizer.vehicle_detected"

# Attributes
ATTR_PLATE = "plate"
ATTR_CONFIDENCE = "confidence"
ATTR_REGION_CODE = "region_code"
ATTR_VEHICLE_TYPE = "vehicle_type"
ATTR_ORIENTATION = "orientation"
ATTR_BOX_Y_CENTRE = "box_y_centre"
ATTR_BOX_X_CENTRE = "box_x_centre"
ATTR_MMC = "mmc"
ATTR_WATCHED_PLATES = "watched_plates"
ATTR_STATISTICS = "statistics"
ATTR_CALLS_REMAINING = "calls_remaining"
ATTR_LAST_DETECTION = "last_detection"
ATTR_PLATES_DETECTED = "plates_detected"
=======
"""Constants for the Plate Recognizer integration."""

DOMAIN = "platerecognizer"

# API
API_URL_CLOUD = "https://api.platerecognizer.com/v1/plate-reader/"
API_URL_STATISTICS = "https://api.platerecognizer.com/v1/statistics/"

# Config entry keys
CONF_API_TOKEN = "api_token"
CONF_CAMERA_ENTITY = "camera_entity"
CONF_REGIONS = "regions"
CONF_WATCHED_PLATES = "watched_plates"
CONF_SAVE_FILE_FOLDER = "save_file_folder"
CONF_SAVE_TIMESTAMPED = "save_timestamped_file"
CONF_ALWAYS_SAVE_LATEST = "always_save_latest_file"
CONF_MMC = "mmc"
CONF_DETECTION_RULE = "detection_rule"
CONF_REGION_MODE = "region_mode"
CONF_SERVER = "server"
CONF_ON_PREMISE = "on_premise"

# Defaults
DEFAULT_MMC = False
DEFAULT_DETECTION_RULE = "none"
DEFAULT_REGION_MODE = "none"
DEFAULT_ON_PREMISE = False
DEFAULT_SERVER = "http://localhost:8080"
DEFAULT_SAVE_TIMESTAMPED = False
DEFAULT_ALWAYS_SAVE_LATEST = False

# Options
DETECTION_RULES = ["none", "strict"]
REGION_MODES = ["none", "strict"]

# Events — dot notation matches original integration
EVENT_VEHICLE_DETECTED = "platerecognizer.vehicle_detected"

# Attributes
ATTR_PLATE = "plate"
ATTR_CONFIDENCE = "confidence"
ATTR_REGION_CODE = "region_code"
ATTR_VEHICLE_TYPE = "vehicle_type"
ATTR_ORIENTATION = "orientation"
ATTR_BOX_Y_CENTRE = "box_y_centre"
ATTR_BOX_X_CENTRE = "box_x_centre"
ATTR_MMC = "mmc"
ATTR_WATCHED_PLATES = "watched_plates"
ATTR_STATISTICS = "statistics"
ATTR_CALLS_REMAINING = "calls_remaining"
ATTR_LAST_DETECTION = "last_detection"
ATTR_PLATES_DETECTED = "plates_detected"
>>>>>>> 6d11309c36a402dcef785300801a53539221bb28
