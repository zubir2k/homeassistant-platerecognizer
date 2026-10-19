"""Constants for the Plate Recognizer integration."""

from __future__ import annotations

DOMAIN = "platerecognizer"

CLOUD_READ_URL = "https://api.platerecognizer.com/v1/plate-reader/"
CLOUD_USAGE_URL = "https://api.platerecognizer.com/v1/statistics/"
CLOUD_DASHBOARD_URL = "https://app.platerecognizer.com/service/snapshot-cloud/"

# Setup (config entry data)
OPT_TOKEN = "api_token"
OPT_CAMERA = "camera_entity"
OPT_LOCAL_SDK = "use_local_sdk"
OPT_SDK_URL = "sdk_url"

# Options
OPT_COUNTRIES = "countries"
OPT_WATCHLIST = "watchlist"
OPT_PLATE_IN_VEHICLE_ONLY = "plate_in_vehicle_only"
OPT_MATCH_COUNTRY_FORMAT = "match_country_format"
OPT_VEHICLE_DETAILS = "vehicle_details"
OPT_SNAPSHOT_DIR = "snapshot_dir"
OPT_SNAPSHOT_KEEP_HISTORY = "snapshot_keep_history"
OPT_SNAPSHOT_EVERY_SCAN = "snapshot_every_scan"

DEFAULT_SDK_URL = "http://localhost:8080"

# Fired once per plate found in a scan
EVENT_PLATE_READ = "platerecognizer_plate_read"

# Watchlist fuzzy match: max differing characters
WATCHLIST_TOLERANCE = 2
