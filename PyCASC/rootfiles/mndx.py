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

class MNDX_GeneralArray:
    def __init__(self,f,cb,el_len=4):
        """ Read a binary array with cb being each element's structure handler """

        self.byte_count = var_int(f,8)
        assert self.byte_count  % el_len == 0, f"Bytelen {self.byte_count } does not match ellen {el_len}"
        self.num_elements = self.byte_count // el_len

        assert self.num_elements < 10000000, f"Array WAY too big (s:{self.num_elements}), definitely a bug"

        self.data=[]
        for x in range(self.num_elements):
            self.data.append(cb(f))
        f.seek((0-int(self.byte_count))&0x07,1)

class MNDX_IntArray:
    def __init__(self,f):
        genarr = MNDX_GeneralArray(f,lambda f: var_int(f,4), el_len=4)
        self.byte_count = genarr.byte_count
        self.num_elements = genarr.num_elements
        self.data = genarr.data

class MNDX_BitArray:
    def __init__(self,f):
        self.array = MNDX_IntArray(f)
        self.bits_per_ent = var_int(f,4)
        self.entry_bitmask = var_int(f,4)
        self.total_elements = var_int(f,8)

        assert self.bits_per_ent * self.total_elements / 32 <= self.array.num_elements, "Invalid BitArray"

class MNDX_SparseArray:
    def __init__(self,f):
        self.itembits = MNDX_IntArray(f)
        self.totalitems,self.validitems = var_int(f,4), var_int(f,4)
        assert self.validitems <= self.totalitems, f"{self.validitems} < {self.totalitems}"
        self.basevals = MNDX_GeneralArray(f,lambda f:(var_int(f,3)),el_len=3) # each el has 3 bytes.
        self.intarr1 = MNDX_IntArray(f)
        self.intarr2 = MNDX_IntArray(f)

class MNDX_HashTable:
    def __init__(self, f):
        pass


class MARFileDB:
    def parse_filedb(self, f):
        hdr = f.read(4)

        assert hdr == b'MAR\0', "Incorrect fdb header "+str(hdr)

        self.CollisionTable = MNDX_SparseArray(f)
        self.FileNameIndexes = MNDX_SparseArray(f)
        self.CollisionHiBitsIndexes = MNDX_SparseArray(f)
        self.LoBitsTable = MNDX_GeneralArray(f,lambda f:f.read(1),el_len=1)
        self.HiBitsTable = MNDX_BitArray(f) # this should be a custom class, but i cba
        self.PathFragments = MNDX_GeneralArray(f,lambda f:f.read(1),el_len=1)
        self.PathMarks = MNDX_SparseArray(f)

        if self.CollisionHiBitsIndexes.validitems != 0 and self.PathFragments.validitems == 0:
            self.childDb = MARFileDB()
            self.childDb.parse_filedb(f)

        self.HashTable = MNDX_HashTable(f)

        # if self.PathFragmentTable

def parse_mndx_root(fd):
    f = BytesIO(fd)
    assert f.read(4) == b'MNDX'

    hver,fver = struct.unpack("II",f.read(8))
    assert 1 <= fver <= 2, "Unsupported MNDX root v"+str(fver)

    if hver == 2:
        f.seek(8,1)

    mio, mic, mis = struct.unpack("III", f.read(12))
    
    ckeo, ckec, fnc, ckes = struct.unpack("IIII", f.read(16))
    assert mic <= 3 and mis == 20, f"mic={mic} | mis={mis}"

    marfiles = []
    for mc in range(mic):
        m = MARFileDB()
        
        f.seek(mio + mc * mis)
        idx,size,size_h,off,off_h = struct.unpack("5I",f.read(20))

        f.seek(off)
        m.parse_filedb(f)

        marfiles.append(m)

    return []