"Configuration settings & logging setup"

import logging

# used for reading the config file
ENCODING = "utf-8"

LOG_FORMAT = "[%(asctime)s]: %(message)s"
LOG_DATEFORMAT = '%H:%M:%S'
SEENMAILS_FILENAME = "pygmailarchive.seenmails"

logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, datefmt=LOG_DATEFORMAT)
logger=logging.getLogger("gmailarchive")
