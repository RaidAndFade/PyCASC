from io import BytesIO
import struct
import pathlib
from PyCASC.utils.CASCUtils import read_cstr, var_int, NAMED_FILE, SNO_FILE, SNO_INDEXED_FILE
from PyCASC.utils.blizzutils import byteskey_to_hex

def parse_hearthstone_root(fd):
    name_map = []
    if isinstance(fd,bytes):
        fd = fd.decode("utf-8")

    for x in fd.splitlines():
        filepath,unk,ckey = x.split("|")
        name_map.append((NAMED_FILE,filepath,ckey))
    return name_map