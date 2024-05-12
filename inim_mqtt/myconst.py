import os
_1_sec = 1
_1_hour = _1_sec * 60 * 60
_12_hours = _1_hour * 12
_1_day = _1_hour * 24
_1_week = _1_day * 7
_1_month = _1_day * 30
_1_year = _1_day * 365
_INFO = "\033[92m"  # GREEN
_WARNING = "\033[93m"  # YELLOW
_ERROR = "\033[91m"  # RED
_DEBUG = "\033[95m"  # MAGENTA
_RESET = "\033[0m"  # RESET

# Logging
LOGLEVEL = os.getenv("LOGLEVEL", "INFO")

# Inim Authentication
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
PIN = os.getenv("PIN")
CLIENTID = os.getenv("CLIENTID")
CLIENTNAME = os.getenv("CLIENTID")
DEVICEID = os.getenv("DEVICEID")
MAXPOLL_TIME = os.getenv("MAXPOLL_TIME", 30 * _1_sec)
MAXAUTHENTICATE_TIME = 300 * _1_sec



# Redis
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_DB = os.getenv("REDIS_DB", "0")