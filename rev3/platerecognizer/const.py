"""Constants for the Plate Recognizer integration."""

DOMAIN = "platerecognizer"

# API
API_URL_CLOUD = "https://api.platerecognizer.com/v1/plate-reader/"
API_URL_USAGE = "https://api.platerecognizer.com/v1/statistics/"

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
CONF_SERVER = "server"          # On-premise SDK URL
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

# Events
EVENT_VEHICLE_DETECTED = f"{DOMAIN}_vehicle_detected"

# Attributes
ATTR_PLATE = "plate"
ATTR_CONFIDENCE = "confidence"
ATTR_REGION = "region"
ATTR_VEHICLE_TYPE = "vehicle_type"
ATTR_ORIENTATION = "orientation"
ATTR_MMC = "mmc"
ATTR_WATCHED_PLATES = "watched_plates"
ATTR_STATISTICS = "statistics"
ATTR_CALLS_REMAINING = "calls_remaining"
ATTR_LAST_DETECTION = "last_detection"
ATTR_PLATES_DETECTED = "plates_detected"

# Sensor platforms
PLATFORMS = ["image_processing"]
