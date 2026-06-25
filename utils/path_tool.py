import os

def get_projiect_root() -> str:
    curent_file = os.path.abspath(__file__)
    curent_dir = os.path.dirname(curent_file)
    return os.path.dirname(curent_dir)

def get_abs_path(filePath:str) ->str :
    return os.path.join(get_projiect_root(),filePath) 