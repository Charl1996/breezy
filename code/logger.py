import logging
from configs import LOG_FILE

logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = logging.FileHandler(LOG_FILE)
logger.addHandler(handler)


def log(message):
    logger.info(message)
