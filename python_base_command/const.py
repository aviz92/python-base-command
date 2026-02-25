import os

from python_base_toolkit.utils.date_time import get_current_date_time_str

LOG_FORMAT = os.getenv("PYTHON_BASE_COMMAND_LOG_FORMAT", "%(asctime)s | %(levelname)s | %(message)s")
LOG_FILE = os.getenv("PYTHON_BASE_COMMAND_LOG_FILE", "true").lower() == "true"
CURRENT_DATE_TIME_STR = get_current_date_time_str()
