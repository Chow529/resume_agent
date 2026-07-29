import os

def get_projiect_root() -> str:
    curent_file = os.path.abspath(__file__)
    return os.path.dirname(os.path.dirname(curent_file))

def get_abs_path(filePath:str) ->str :
    return os.path.join(get_projiect_root(),filePath)


if __name__ == "__main__":
    print(get_projiect_root())
