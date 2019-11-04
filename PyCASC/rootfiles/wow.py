import struct
from io import BytesIO
from PyCASC.utils.CASCUtils import read_cstr, var_int, NAMED_FILE, SNO_FILE, SNO_INDEXED_FILE, WOW_HASHED_FILE, WOW_DATAID_FILE

WOWROOT_FORMAT_82 = "82"
WOWROOT_FORMAT_6x = "6x"

class WOWROOT_GroupHeader:
    def __init__(self, f):
        dat = f.read(12)
        self.valid = True
        if len(dat)==12:
            self.number_of_files,self.content_flags,self.locale_flags = struct.unpack("3I",dat)
        else:
            self.valid = False


class WOWROOT_Group:
    def __init__(self, f, root_format, handler):
        self.header = WOWROOT_GroupHeader(f)
        if not self.header.valid:
            return

        self.hashes = None
        self.ckeys = None
        self.entries = None
        self.file_data_ids = [var_int(f,4) for x in range(self.header.number_of_files)]
        handler.file_count += self.header.number_of_files

        if root_format == WOWROOT_FORMAT_82:
            self.ckeys = [f.read(0x10) for x in range(self.header.number_of_files)]
            
            if handler.file_count > handler.hashless_count:
                self.hashes = [struct.unpack("Q",f.read(8)) for x in range(self.header.number_of_files)]

        elif root_format == WOWROOT_FORMAT_6x:
            self.entries = [(f.read(0x10),struct.unpack("Q",f.read(8))) for x in range(self.header.number_of_files)]

        else:
            raise f"Invalid Root Format {root_format}"

class WOWROOT_Handler:
    def __init__(self, f, root_format, hashless_count):
        self.f = f
        self.root_format = root_format
        self.hashless_count = hashless_count
        self.files = []

    def load_groups(self, localeMask, override, audioGroup):
        self.file_count = 0
        while True:
            g = WOWROOT_Group(self.f,self.root_format,self)
            if not g.header.valid:
                break

            if (g.header.content_flags & 0x100) > 0:
                continue

            if (g.header.content_flags & 0x80) > 0 and override == 0:
                continue

            if (g.header.content_flags >> 0x1f) != audioGroup:
                continue

            if localeMask != 0 and (g.header.locale_flags & localeMask) == 0:
                continue

            if self.root_format == WOWROOT_FORMAT_82:
                fid = 0
                for x in range(g.header.number_of_files):
                    fid += g.file_data_ids[x]
                    fid &= 0xffffffff # the c equivalent here wraps around to negatives.
                    self.files.append([fid,g.ckeys[x],g.hashes[x] if g.hashes is not None else 0])
                    fid += 1

    def load_audio_group(self, localeMask, audioGroup):
        p = self.f.tell()
        self.load_groups(localeMask,False,audioGroup)
        self.f.seek(p)

    def load(self, localeMask):
        self.load_audio_group(localeMask,0)
        self.load_audio_group(localeMask,1)
        

def parse_82_hdr(f):
    sig,item_count,namehash_count = struct.unpack("3I",f.read(12))

    if sig != 0x4D465354:
        return False
    
    if namehash_count > item_count:
        return False

    return (item_count,namehash_count)

def parse_wow_root(fd):
    f = BytesIO(fd)
    hashless_count = 0
    root_format = WOWROOT_FORMAT_82

    hdr = parse_82_hdr(f)

    if not hdr: # header is not 82, must be 6x
        f.seek(-12,1)
        root_format = WOWROOT_FORMAT_6x
    else:
        hashless_count = hdr[0]-hdr[1]
        
    root_handle = WOWROOT_Handler(f,root_format,hashless_count)

    root_handle.load(0xffffffff) # load all locales
    root_handle.load(0x01) # load all locales

    name_map = []
    
    for x in root_handle.files:
        name_map.append((WOW_DATAID_FILE,x[0],x[1]))

    return name_map