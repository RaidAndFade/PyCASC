
from PyCASC.utils.CASCUtils import read_cstr, NAMED_FILE, SNO_FILE, SNO_INDEXED_FILE

def parse_ow_root(fd):
    name_map = []
    
    if isinstance(fd,bytes):
        fd = fd.decode("utf-8")

    skipfirst = False
    for l in fd.splitlines():
        if not skipfirst:
            skipfirst=True
            continue
        ld = l.split("|")

        name_map.append((NAMED_FILE,ld[0],ld[1]))

    return name_map