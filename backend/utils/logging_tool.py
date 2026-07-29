import logging
import os
from datetime import datetime
from utils.path_tool import get_abs_path


LOG_ROOT = get_abs_path("log")

os.makedirs(LOG_ROOT,exist_ok= True)

DEFAULT_LOG_FORMAT =  logging.Formatter(
    '%(asctime)s-%(name)s-%(levelname)s-%(filename)s-%(levelno)s-%(message)s'
)



def get_logger(
        name:str = "agent",
        console_level :int = logging.INFO,
        file_level : int = logging.DEBUG,
        log_file:str = None # type: ignore
)-> logging.Logger :
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if logger.handlers :
        return logger
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(DEFAULT_LOG_FORMAT)
    logger.addHandler(console_handler)

    if not log_file :
        log_file = os.path.join(LOG_ROOT,f'{name}_{datetime.now().strftime("%d%m%Y")}.log')

    file_handler = logging.FileHandler(log_file,encoding="utf-8")
    file_handler.setLevel(file_level)
    file_handler.setFormatter(DEFAULT_LOG_FORMAT)
    logger.addHandler(file_handler)

    return logger


logger = get_logger()