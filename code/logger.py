import logging
from configs import LOG_FILE
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = logging.FileHandler(LOG_FILE)
logger.addHandler(handler)


def log(message):
    logger.info(f'[{datetime.today()}] {message}')
