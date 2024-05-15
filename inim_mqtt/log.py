import logging
import myconst

def _quit(*vargs, **kwargs):
    logging.error(*vargs, **kwargs)
    raise SystemExit

logging.quit = _quit

def setup_custom_logger(name):
    logging.basicConfig(
        format="{asctime} [{levelname}] {message}", style="{", level=myconst.LOGLEVEL
    )
    logging.addLevelName(logging.INFO, myconst._INFO + logging.getLevelName(logging.INFO) + myconst._RESET)
    logging.addLevelName(
        logging.WARNING, myconst._WARNING + logging.getLevelName(logging.WARNING) + myconst._RESET
    )
    logging.addLevelName(
        logging.ERROR, myconst._ERROR + logging.getLevelName(logging.ERROR) + myconst._RESET
    )
    logging.addLevelName(
        logging.DEBUG, myconst._DEBUG + logging.getLevelName(logging.DEBUG) + myconst._RESET
    )

    # formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(module)s - %(message)s')

    handler = logging.StreamHandler()
    # handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    # logger.setLevel(logging.DEBUG)
    logger.setLevel(myconst.LOGLEVEL)
    logger.addHandler(handler)
    logger.debug('Loading logging condifiguration for %s.', name)

    return logger