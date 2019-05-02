import struct
from io import BytesIO
from blizzutils import byteskey_to_hex

def beautify_filesize(i):
    t,c=["","K","M","G","T"],0
    while i>1024:i/=1024;c+=1
    return str(round(i,2))+t[c]+"B"
    
def parse_encoding_file(fd):
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
    ckey_data = d.read(0x20*ckey_pagecount+ckey_pagesize*ckey_pagecount)
    ckey_map = _parse_ckey_pages(ckey_data,ckey_len,ekey_len,ckey_pagesize,ckey_pagecount)

    return ckey_map # i could do more here, but this is the only thing i actually need so idgaf.

def _parse_ckey_pages(ckey_data,ckey_len,ekey_len,ckey_pagesize,ckey_pagecount):
    d=BytesIO(ckey_data)
    headerlen=0x20*ckey_pagecount
    # d.seek(0x20*ckey_pagecount,1) # read the index table
    ckey_map = {}
    for i in range(ckey_pagecount):
        d.seek(headerlen + i * ckey_pagesize)
        while True:
            ekcount, = struct.unpack("H",d.read(2))
            if ekcount==0:
                break
            d.seek(4,1)
            # cfsize, = struct.unpack(">i",d.read(4))
            ckey = byteskey_to_hex(d.read(ckey_len))
            # assert ekcount == len(ekeys)
            ckey_map[ckey]=[byteskey_to_hex(d.read(ekey_len)) for x in range(ekcount)]
    return ckey_map

def _r_casc_dataheader(f):
    blth,sz,f_0,f_1,chkA,chkB=struct.unpack("16sI2b4s4s",f.read(30))
    return blth,sz,f_0,f_1,chkA,chkB
def _r_casc_blteheader(f):
    assert f.read(4) == b"BLTE"
    sz,flg,cc=struct.unpack("IB3s",f.read(8))
    cc=int.from_bytes(cc,'big',signed=False)

    chunks=[]
    for _ in range(cc):
        chunks.append(struct.unpack(">II16s",f.read(24)))
        #compressedSize,decomressedSize,16byte checksum
    return sz,flg,cc,chunks

def _r_casc_bltechunk(f,ci):
    etype=f.read(1)
    if etype==b"N": #plain data
        return f.read(ci[1])
    elif etype==b"Z":
        import zlib
        return zlib.decompress(f.read(ci[0]-1))
    else:
        raise Exception(f"Fuck you {etype} encoding")

def cascfile_size(data_path,data_index,offset,size):
    size=0
    with open(f"{data_path}data.{data_index:03d}","rb") as df:
        df.seek(offset+30) # fuck my ass
        # data_header = _r_casc_dataheader(df)
        blte_header = _r_casc_blteheader(df)
        for c in blte_header[3]: # for each chunk
            size+=c[1]
    return size

def r_cascfile(data_path,data_index,offset,size):
    # datafile = r_data(f"{data_path}data.{data_index:03d}")
    data = b''
    with open(f"{data_path}data.{data_index:03d}","rb") as df:
        df.seek(offset)
        data_header = _r_casc_dataheader(df)
        blte_header = _r_casc_blteheader(df)
        for c in blte_header[3]: # for each chunk
            chunk_data = _r_casc_bltechunk(df,c)
            data += chunk_data
    return data


def read_cstr(f):
    s=b''
    while True:
        c=f.read(1)
        if c == b'\x00':
            break
        s += c
    return str(s,"utf-8")

#ROOT FILES === THIS SECTION WILL BE LARGE.
SNO_FILE=0
SNO_INDEXED_FILE=1
NAMED_FILE=2

def _parse_plaintext_root(fd):
    name_map = []
    for x in fd.splitlines():
        filepath,ckey,flags = x.decode("utf-8").split("|")
        name_map.append((NAMED_FILE,filepath,ckey))
    return name_map

def _parse_d3_root_entry(df,t):
    ckey = byteskey_to_hex(df.read(16))
    i=""
    fi=0
    if t is SNO_FILE or t is SNO_INDEXED_FILE:
        snoid=str(struct.unpack("I",df.read(4)))
        if t is SNO_INDEXED_FILE:
            findex=str(struct.unpack("I",df.read(4)))
            return t,(snoid,findex),ckey
        else:
            return t,snoid,ckey
    elif t is NAMED_FILE:
        return t,read_cstr(df),ckey


def _parse_d3_root(fd,cr):
    f = BytesIO(fd)
    sig = f.read(4)
    count, = struct.unpack("I",f.read(4))
    named_entries = []
    sno_entries = []
    dirs = []
    for _ in range(count):
        ckey=f.read(16)
        name=read_cstr(f)
        dirs.append((name,ckey))

    for name,ckey in dirs:
        dirfile = cr.get_file_by_ckey(byteskey_to_hex(ckey))
        if dirfile is None:
            continue
        df = BytesIO(dirfile)
        dfmagic = df.read(4)
        with open(f"d3dirfiles/{name}.dirfile","wb+") as f:
            f.write(dirfile)

        snocount, = struct.unpack("I",df.read(4))
        for _ in range(snocount):
            e = _parse_d3_root_entry(df,SNO_FILE)+(name,)
            sno_entries.append(e)
        
        snoidx_count, = struct.unpack("I",df.read(4))
        for _ in range(snoidx_count):
            e = _parse_d3_root_entry(df,SNO_INDEXED_FILE)+(name,)
            sno_entries.append(e)

        namecount, = struct.unpack("I",df.read(4))
        for _ in range(namecount):
            e = _parse_d3_root_entry(df,NAMED_FILE)+(name,)
            named_entries.append(e)


    from casc.SNO import _parse_d3_coretoc

    # print ([c[2] for c in named_entries])
    # coretoc_ckey = [c for c in named_entries if c[1]=="CoreTOC.dat"][0]
    # sno_table = _parse_d3_coretoc(cr.get_file_by_ckey(coretoc_ckey))

    return named_entries

def parse_root_file(uid,fd,cascreader):
    """Returns an array of format [TYPE, ID, CKEY, EXTRA...],
    Type = one of NAMED_FILE, SNO_FILE, SNO_INDEXED_FILE
    Id = depends on type. NAMED:"strname", SNO:"snoid", SNO_INDEXED:("snoid","index")
    Ckey = that file's ckey
    Extra = uid specific data 
        d3: extra is the directory that the file is in
    """
    if uid in ["w3"]:
        return _parse_plaintext_root(fd)
    elif uid in ['d3']:
        return _parse_d3_root(fd,cascreader)
    else:
        with open(f"{uid}.rootfile","wb+") as f:
            f.write(fd)
        raise Exception(f"Don't know how to read root file for {uid}. Dumped contents to {uid}.rootfile")
