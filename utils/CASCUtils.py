import struct
from io import BytesIO
from utils.blizzutils import byteskey_to_hex

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
    ckey_map = _parse_ckey_pages(d,ckey_len,ekey_len,ckey_pagesize,ckey_pagecount)

    return ckey_map # i could do more here, but this is the only thing i actually need so idgaf.

def _parse_ckey_pages(d,ckey_len,ekey_len,ckey_pagesize,ckey_pagecount):
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
            ckey_map[ckey]=int.from_bytes(d.read(ekey_len)[:9],byteorder='big')
            # [byteskey_to_hex(d.read(ekey_len)) for x in range(ekcount)][0]
            d.seek(ekey_len*(ekcount-1),1)
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

def cascfile_size(data_path,data_index,offset):
    size=0
    chunkcount=0
    with open(f"{data_path}data.{data_index:03d}","rb") as df:
        df.seek(offset+30) # fuck my ass
        # data_header = _r_casc_dataheader(df)
        blte_header = _r_casc_blteheader(df)
        chunkcount=len(blte_header[3])
        for c in blte_header[3]: # for each chunk
            size+=c[1]
    return size, chunkcount

def r_cascfile(data_path,data_index,offset,max_size=-1):
    """ Reads a given cascfile, reading as many chunks as needed to get *at least* max_size bytes."""
    # datafile = r_data(f"{data_path}data.{data_index:03d}")
    data = BytesIO()
    with open(f"{data_path}data.{data_index:03d}","rb") as df:
        df.seek(offset)
        # data_header = _r_casc_dataheader(df)
        df.seek(30,1)
        blte_header = _r_casc_blteheader(df)
        ds = 0
        for c in blte_header[3]: # for each chunk
            chunk_data = _r_casc_bltechunk(df,c)
            data.write(chunk_data)
            ds += c[1]
            if max_size>0 and ds>max_size:
                break
    return data.getbuffer()

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
    return s.decode("utf-8")

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
    if t is SNO_FILE or t is SNO_INDEXED_FILE:
        snoid,=struct.unpack("I",df.read(4))
        if t is SNO_INDEXED_FILE:
            findex,=struct.unpack("I",df.read(4))
            return t,(snoid,findex),ckey
        else:
            return t,snoid,ckey
    elif t is NAMED_FILE:
        return t,read_cstr(df),ckey

def _parse_d3_root(fd,cr):
    f = BytesIO(fd)
    sig = f.read(4)
    count, = struct.unpack("I",f.read(4))
    final_entries = []
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
            final_entries.append(e) 
            # add them directly to the final entries, since these are basically the final results for this type of entry


    from utils.casc.SNO import _parse_d3_coretoc, _parse_d3_packages

    # print ([c[2] for c in named_entries])
    coretoc_ckey = [c for c in final_entries if c[1]=="CoreTOC.dat"][0][2]
    sno_table = _parse_d3_coretoc(cr.get_file_by_ckey(coretoc_ckey)) # snid : (name,sngrp,grpnm,grpext)

    packages_ckey = [c for c in final_entries if c[1]=="Data_D3\\PC\\Misc\\Packages.dat"][0][2]
    pkg_table = _parse_d3_packages(cr.get_file_by_ckey(packages_ckey))

    for sf in sno_entries:
        if sf[0]==SNO_FILE:
            if sf[1] in sno_table: # if this file is in the sno_table, then we know it's name
                sfn = sno_table[sf[1]]
                final_entries.append((NAMED_FILE,f"{sfn[2]}/{sfn[0]}.{sfn[3]}",sf[2]))
            else: # otherwise, we dont know the name.
                final_entries.append((SNO_FILE,sf[1],sf[2]))
        else: # sf is SNO_INDEXED_FILE
            pass
            # if sf[1][0] in sno_table: # if this file is in the sno_table, then we know it's name
            #     sfn = sno_table[sf[1][0]]
            #     final_entries.append((NAMED_FILE,f"{sfn[2]}/{sfn[0]}.{sfn[3]}",sf[2]))
            # else: # otherwise, we dont know the name.
            #     final_entries.append((SNO_FILE,sf[1],sf[2]))

    return final_entries

def parse_root_file(uid,fd,cascreader):
    """Returns an array of format [TYPE, ID, CKEY, EXTRA...],
    Type = one of NAMED_FILE, ID_FILE, ID_INDEXED_FILE
    Id = depends on type. NAMED:"strname", ID:"id", ID_INDEXED:("id","index")
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
