import struct
from io import BytesIO
from typing import List
from PyCASC import TACT_KEYS
from PyCASC.utils.blizzutils import byteskey_to_hex, var_int

def beautify_filesize(i):
    t,c=["","K","M","G","T"],0
    while i>1024:i/=1024;c+=1
    return str(round(i,2))+t[c]+"B"
    
def parse_encoding_file(fd,whole_key=False):
    d=BytesIO(fd)
    assert d.read(2) == b"EN"
    version,ckey_len,ekey_len = struct.unpack("3B",d.read(3))
    ckey_pagesize = int.from_bytes(d.read(2),'big')*1024
    ekey_pagesize = int.from_bytes(d.read(2),'big')*1024
    ckey_pagecount = int.from_bytes(d.read(4),'big')
    ekey_pagecount = int.from_bytes(d.read(4),'big')
    d.seek(1,1) #unk_1
    espec_blocksize = int.from_bytes(d.read(4),'big')

    # print(version,ckey_len,ekey_len,ckey_pagesize,ekey_pagesize,ckey_pagecount,ekey_pagecount,espec_blocksize)
    espec_data = d.seek(espec_blocksize,1)
    ckey_map = _parse_ckey_pages(d,ckey_len,ekey_len,ckey_pagesize,ckey_pagecount,whole_key)

    return ckey_map # i could do more here, but this is the only thing i actually need so idgaf.

def _parse_ckey_pages(d,ckey_len,ekey_len,ckey_pagesize,ckey_pagecount,whole_key):
    a=d.tell()
    headerlen=0x20*ckey_pagecount
    # d.seek(0x20*ckey_pagecount,1) # read the index table
    ckey_map = {}
    for i in range(ckey_pagecount):
        d.seek(headerlen + i * ckey_pagesize+a)
        while True:
            ekcount = struct.unpack("H",d.read(2))[0]
            if ekcount==0:
                break
            d.seek(4,1)
            # cfsize, = struct.unpack(">i",d.read(4))
            ckey = int.from_bytes(d.read(ckey_len),byteorder='big')
            # assert ekcount == len(ekeys)
            if whole_key:
                ckey_map[ckey]=int.from_bytes(d.read(ekey_len),byteorder='big')
            else:
                ckey_map[ckey]=int.from_bytes(d.read(ekey_len)[:9],byteorder='big')
            # [byteskey_to_hex(d.read(ekey_len)) for x in range(ekcount)][0]
            d.seek(ekey_len*(ekcount-1),1)
    return ckey_map

class INTag:
    name:str
    tagtype:int
    flags:List[int]

class INEntry:
    name:str
    md5:int
    size:int
    tags:List[INTag]

def parse_install_file(fd):
    f = BytesIO(fd)

    assert f.read(2) == b"IN"
    b1,b2 = f.read(2)

    tag_num = int.from_bytes(f.read(2),byteorder="big")
    file_num = int.from_bytes(f.read(4),byteorder="big")
    mask_len = (file_num + 7) // 8

    tags = []
    for x in range(tag_num):
        t = INTag()
        t.name = read_cstr(f)
        t.tagtype = int.from_bytes(f.read(2),byteorder="little")
        t.flags = []

        for y in range(mask_len):
            bd = f.read(1)[0]
            bd = (((bd * 0x0202020202) & 0x010884422010) % 1023) 
            for z in range(8):
                if (bd & (2 ** z)) > 0:
                    t.flags.append(y*8+z)
        tags.append(t)

    files = []
    for x in range(file_num):
        e = INEntry()
        e.name = read_cstr(f)
        e.md5 = var_int(f,16,False)
        e.size = var_int(f,4,False)
        e.tags = [t.name for t in tags if x in t.flags]
        files.append(e)

    return files

class DLEntry:
    key:bytes
    index:int
    tags:List[str]

def parse_download_file(fd):
    f = BytesIO(fd)

    assert f.read(2) == b"DL"
    b1,b2,b3 = f.read(3)

    file_num = int.from_bytes(f.read(4),byteorder="big")
    tag_num = int.from_bytes(f.read(2),byteorder="big")

    mask_len = (file_num + 7) // 8

    dl_entries = []

    for x in range(file_num):
        ck = f.read(16) # hash
        f.seek(0xA,1) # unk

        dle = DLEntry()
        dle.key = ck
        dle.index = x
        dle.tags = []
        dl_entries.append(dle)

    f.read(5) # idfk.

    for x in range(tag_num):
        tagname = read_cstr(f)
        tagtype = int.from_bytes(f.read(2),byteorder="little")

        for y in range(mask_len):
            bd = f.read(1)[0]
            bd = (((bd * 0x0202020202) & 0x010884422010) % 1023) 
            for z in range(8):
                # print(f"[{tagname}] {bd:b} & {2**z:b}? ({y*8+z})")
                if y*8+z < len(dl_entries) and (bd & (2 ** z)) > 0:
                    dl_entries[y*8+z-1].tags.append(tagname)
    
    return dl_entries

def _r_casc_dataheader(f):
    blth,sz,f_0,f_1,chkA,chkB=struct.unpack("16sI2b4s4s",f.read(30))
    return blth,sz,f_0,f_1,chkA,chkB

def _r_casc_blteheader(f):
    assert f.read(4) == b"BLTE"
    sz, = struct.unpack("I",f.read(4))
    if sz == 0: # single chunk. 
        return 0,0,1,[(-1,-1,b'')]
    
    flg,cc=struct.unpack("B3s",f.read(4))
    cc=int.from_bytes(cc,'big',signed=False)

    chunks=[]
    for _ in range(cc):
        chunks.append(struct.unpack(">II16s",f.read(24)))
        #compressedSize,decomressedSize,16byte checksum
    return sz,flg,cc,chunks

def _r_casc_bltechunk(f,ci):
    etype=f.read(1)
    if etype==b"N": #plain data
        return f.read(ci[1] if ci[1]>0 else -1)
    elif etype==b"Z":
        import zlib
        return zlib.decompress(f.read(ci[0]-1 if ci[1]>0 else -1))
    elif etype==b"E":
        keyname_len = var_int(f,1)
        keyname = f.read(keyname_len)
        iv_len = var_int(f,1)
        iv = f.read(iv_len)
        ktype = f.read(1)
        data = f.read(ci[0]-1-keyname_len-1-iv_len-1-1)

        retdata = b''
        if keyname in TACT_KEYS:
            key = TACT_KEYS[keyname]
            try:
                import salsa20
                retdata = salsa20.Salsa20_xor(data,iv,key)
            except:
                print("Attempted to use salsa20 package to extract encrypted data, but it was not installed")
        return retdata
    else:
        raise Exception(f"Fuck you {etype} encoding")

def parse_blte(df,read_data=True,max_size=-1):
    if isinstance(df,bytes):
        df=BytesIO(df)
    blte_header=_r_casc_blteheader(df)
    blte_data,ds = BytesIO(),0
    if read_data:
        for c in blte_header[3]: # for each chunk
            chunk_data = _r_casc_bltechunk(df,c)
            blte_data.write(chunk_data)
            ds += c[1]
            if max_size>0 and ds>max_size:
                break
    return blte_header, blte_data.getvalue()

def cascfile_size(data_path,data_index,offset):
    size=0
    chunkcount=0
    with open(f"{data_path}data.{data_index:03d}","rb") as df:
        df.seek(offset+30) # fuck my ass
        # r_casc_dataheader(df)
        blte_header,dbfr=parse_blte(df,False)
        chunkcount=len(blte_header[3])
        for c in blte_header[3]: # for each chunk
            size+=c[1]
    return size, chunkcount

def r_cascfile(data_path,data_index,offset,max_size=-1):
    """ Reads a given cascfile, reading as many chunks as needed to get *at least* max_size bytes."""
    # datafile = r_data(f"{data_path}data.{data_index:03d}")
    data = b''
    with open(f"{data_path}data.{data_index:03d}","rb") as df:
        df.seek(offset)
        data_header = _r_casc_dataheader(df)
        blte_header, data = parse_blte(df,max_size=max_size)
    return data

# import functools
# import itertools

# def readcstr(f):
#     toeof = iter(functools.partial(f.read, 1), '')
#     return ''.join(itertools.takewhile('\0'.__ne__, toeof))

def read_cstr(f):
    s=b''
    c=f.read(1)
    while c != b'\0':
        s+=c
        c=f.read(1)
    try:
        return s.decode("utf-8")
    except UnicodeDecodeError:
        print(f"Failed to decode {s}")

#ROOT FILES === THIS SECTION WILL BE LARGE.
SNO_FILE=0
SNO_INDEXED_FILE=1
NAMED_FILE=2
WOW_HASHED_FILE=3
WOW_DATAID_FILE=4

def parse_root_file(uid,fd,cascreader):
    """Returns an array of format [TYPE, ID, CKEY, EXTRA...],
    Type = one of NAMED_FILE, ID_FILE, ID_INDEXED_FILE
    Id = depends on type. NAMED:"strname", ID:"id", ID_INDEXED:("id","index")
    Ckey = that file's ckey
    Extra = uid specific data 
        d3: extra is the "directory" that the file is in
    """
    from PyCASC.rootfiles import parse_d3_root, parse_wow_root, parse_mndx_root, parse_warcraft3_root, parse_hearthstone_root, parse_ow_root

    if uid in ['hsb']:
        return parse_hearthstone_root(fd)
    elif uid in ["w3"]:
        return parse_warcraft3_root(fd)
    elif uid in ['d3']:
        return parse_d3_root(fd,cascreader)
    elif uid in ['hero','s2']:
        return parse_mndx_root(fd)
    elif uid in ['pro']:
        return parse_ow_root(fd)
    elif uid in ['wow']:
        return parse_wow_root(fd)
    else:
        with open(f"{uid}.rootfile","wb+") as f:
            f.write(fd)
        raise Exception(f"Don't know how to read root file for {uid}. Dumped contents to {uid}.rootfile")
