from io import BytesIO
import struct
import pathlib
from PyCASC.utils.CASCUtils import read_cstr, var_int, NAMED_FILE, SNO_FILE, SNO_INDEXED_FILE
from PyCASC.utils.blizzutils import byteskey_to_hex

class MARInfo:
    idx:int
    size:int
    size_h:int
    off:int
    off_h:int

def read_arr(f,cb):
    """ Read a binary array with cb being each element's structure handler """
    c=var_int(f,4)
    a=[]
    for x in range(c):
        a.append(cb(f))
    return a

def read_int_arr(f):
    return read_arr(f,lambda f:var_int(f,4))

def __parse_mndx_sparsearr(f):
    itembits = read_int_arr(f)
    totalitems,validitems = var_int(f,4), var_int(f,4)
    basevals = read_arr(f,lambda f:(var_int(f,4),var_int(f,4),var_int(f,4))) # each el has 3 ints.
    intarr1 = read_int_arr(f)
    intarr2 = read_int_arr(f)
    

def __parse_mndx_filedb(f,n=False):
    assert n or f.read(4) == b'MAR\0'

def parse_mndx_root(fd):
    f = BytesIO(fd)
    assert f.read(4) == b'MNDX'

    hver,fver = struct.unpack("II",f.read(8))
    assert 1 >= fver >= 2

    if hver == 2:
        f.seek(8,1)
    
    mio, mic, mis = struct.unpack("III", f.read(12))
    mdo, mdc, mdv, mds = struct.unpack("IIII", f.read(16))
    assert mic <= 3 and mis == 20

    marinfos = []
    marfiles = []
    for _ in range(mic):
        m = MARInfo()
        m.idx,m.size,m.size_h,m.off,m.off_h = struct.unpack("5I",f.read(20))
        marinfos.append(m) 
    
        x = f.tell()
        f.seek(m.off)
        db = __parse_mndx_filedb(f)

    return []