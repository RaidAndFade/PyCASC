import struct
from io import BytesIO
from blizzutils import byteskey_to_hex

def parse_encoding_file(fd):
    d=BytesIO(fd)
    assert d.read(2) == b"EN"
    version,ckey_len,ekey_len = struct.unpack("3B",d.read(3))
    ckey_pagesize = int.from_bytes(d.read(2),'big')*1024
    ekey_pagesize = int.from_bytes(d.read(2),'big')*1024
    ckey_pagecount = int.from_bytes(d.read(4),'big')
    ekey_pagecount = int.from_bytes(d.read(4),'big')
    unk_0 = d.read(1)
    espec_blocksize = int.from_bytes(d.read(4),'big')

    # print(version,ckey_len,ekey_len,ckey_pagesize,ekey_pagesize,ckey_pagecount,ekey_pagecount,espec_blocksize)
    espec_data = d.read(espec_blocksize) # i dont fucking know why there's an extra byte
    ckey_data = d.read(0x20*ckey_pagecount+ckey_pagesize*ckey_pagecount)
    ckey_map = _parse_ckey_pages(ckey_data,ckey_len,ekey_len,ckey_pagesize,ckey_pagecount)

    return ckey_map # i could do more here, but this is the only thing i actually need so idgaf.

def _parse_ckey_pages(ckey_data,ckey_len,ekey_len,ckey_pagesize,ckey_pagecount):
    d=BytesIO(ckey_data)
    d.read(0x20*ckey_pagecount) # read the index table
    ckey_map = {}
    for _ in range(ckey_pagecount):
        ckbuf=BytesIO(d.read(ckey_pagesize))
        while ckbuf.readable():
            ekcount, = struct.unpack("H",ckbuf.read(2))
            if ekcount==0:
                break
            cfsize, = struct.unpack(">i",ckbuf.read(4))
            ckey = byteskey_to_hex(struct.unpack(f"{ckey_len}s",ckbuf.read(ckey_len))[0])
            ekeys = [byteskey_to_hex(struct.unpack(f"{ekey_len}s",ckbuf.read(ekey_len))[0]) for x in range(ekcount)]
            assert ekcount == len(ekeys)
            ckey_map[ckey]=ekeys
    return ckey_map

def _r_casc_dataheader(f):
    blth,sz,f_0,f_1,chkA,chkB=struct.unpack("16sI2b4s4s",f.read(30))
    return blth,sz,f_0,f_1,chkA,chkB
def _r_casc_blteheader(f):
    sz,flg,cc=struct.unpack("IB3s",f.read(8))
    cc=int.from_bytes(cc,'big',signed=False)

    chunks=[]
    for _ in range(cc):
        chunks.append(struct.unpack(">II16s",f.read(24)))
    return sz,flg,cc,chunks

def _r_casc_bltechunk(f,ci):
    etype=f.read(1)
    if etype==b"N": #plain data
        return f.read(ci[1])
    elif etype==b"Z":
        import zlib
        return zlib.decompress(f.read(ci[0]-1))
    else:
        print(f"Fuck you {etype} encoding")
        return b''

def r_cascfile(data_path,data_index,offset,size):
    # datafile = r_data(f"{data_path}data.{data_index:03d}")
    data = b''
    with open(f"{data_path}data.{data_index:03d}","rb") as df:
        df.seek(offset)
        data_header = _r_casc_dataheader(df)
        assert df.read(4) == b"BLTE"
        blte_header = _r_casc_blteheader(df)
        for c in blte_header[3]: # for each chunk
            chunk_data = _r_casc_bltechunk(df,c)
            data += chunk_data
    return data


#ROOT FILES === THIS SECTION WILL BE LARGE.
def _parse_plaintext_root(fd):
    name_map = []
    for x in fd.splitlines():
        filepath,ckey,flags = x.decode("utf-8").split("|")
        name_map.append((filepath,ckey))
    return name_map

def parse_root_file(uid,fd):
    """Returns an array of format [nkey,ckey,extra], nkey is whatever identifier this app uses, can be anything really, for wow it's an integer id, for wc3 it's the filename.
    """
    if uid in ["w3"]:
        return _parse_plaintext_root(fd)
    else:
        raise Exception(f"Don't know how to read root file for {uid}")
