import logging

def start_logging(filename, module='pelita'):
    if not filename or filename == '-':
        hdlr = logging.StreamHandler()
    else:
        hdlr = logging.FileHandler(filename, mode='w')
    logger = logging.getLogger(module)
    FORMAT = '[%(relativeCreated)06d %(name)s:%(levelname).1s][%(funcName)s] %(message)s'
    formatter = logging.Formatter(FORMAT)
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    logger.setLevel(logging.DEBUG)

