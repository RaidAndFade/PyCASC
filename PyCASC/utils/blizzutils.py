from typing import Dict,List
import requests
import os
import hashlib
import pickle
from io import BytesIO
from time import time
from PyCASC import CACHE_DIRECTORY, CACHE_DURATION

def parse_config(c) -> List[Dict[str,str]]:
    out = []
    lines = c.split("\n")
    cols = list(map(lambda x:x.split("!")[0],lines[0].split("|")))
    for x in lines[1:]:
        if x[:2]=="##" or x.strip()=="": 
            continue
        row = {}
        i = 0
        for v in x.split("|"):
            row[cols[i]]=v
            i+=1
        out.append(row)
    return out

def parse_build_config(c):
    data = {}
    for l in c.split("\n"):
        if l.strip()=="" or l[0]=="#" or len(l.split(" = "))<2:
            continue
        else:
            n,v=l.split(" = ")
            data[n]=v
    return data

def hexkey_to_bytes(s:str):
    return bytes.fromhex(s)
def byteskey_to_hex(b:bytes):
    return b.hex()
    
def var_int(f:object,l:int,le=True):
    return int.from_bytes(f.read(l), byteorder='little' if le else 'big', signed=False)

def jenkins_hash(key:bytes):
    h=0
    for x in key:
        h+=ord(x)
        h=h&0xffffffff
        h+=h<<10
        h=h&0xffffffff
        h^=h>>6
        h=h&0xffffffff
    h+=h<<3
    h=h&0xffffffff
    h^=h>>11
    h=h&0xffffffff
    h+=h<<15
    h=h&0xffffffff
    return h

def rot(x,k):
    return (((x)<<(k)) | ((x)>>(32-(k))))

def mix(a, b, c):
    a &= 0xffffffff; b &= 0xffffffff; c &= 0xffffffff
    a -= c; a &= 0xffffffff; a ^= rot(c,4);  a &= 0xffffffff; c += b; c &= 0xffffffff
    b -= a; b &= 0xffffffff; b ^= rot(a,6);  b &= 0xffffffff; a += c; a &= 0xffffffff
    c -= b; c &= 0xffffffff; c ^= rot(b,8);  c &= 0xffffffff; b += a; b &= 0xffffffff
    a -= c; a &= 0xffffffff; a ^= rot(c,16); a &= 0xffffffff; c += b; c &= 0xffffffff
    b -= a; b &= 0xffffffff; b ^= rot(a,19); b &= 0xffffffff; a += c; a &= 0xffffffff
    c -= b; c &= 0xffffffff; c ^= rot(b,4);  c &= 0xffffffff; b += a; b &= 0xffffffff
    return a, b, c

def final(a, b, c):
    a &= 0xffffffff; b &= 0xffffffff; c &= 0xffffffff
    c ^= b; c &= 0xffffffff; c -= rot(b,14); c &= 0xffffffff
    a ^= c; a &= 0xffffffff; a -= rot(c,11); a &= 0xffffffff
    b ^= a; b &= 0xffffffff; b -= rot(a,25); b &= 0xffffffff
    c ^= b; c &= 0xffffffff; c -= rot(b,16); c &= 0xffffffff
    a ^= c; a &= 0xffffffff; a -= rot(c,4);  a &= 0xffffffff
    b ^= a; b &= 0xffffffff; b -= rot(a,14); b &= 0xffffffff
    c ^= b; c &= 0xffffffff; c -= rot(b,24); c &= 0xffffffff
    return a, b, c

def hashlittle2(data, initval = 0, initval2 = 0):
    length = lenpos = len(data)

    a = b = c = (0xdeadbeef + (length) + initval)

    c += initval2; c &= 0xffffffff

    p = 0  # string offset
    while lenpos > 12:
        a += (ord(data[p+0]) + (ord(data[p+1])<<8) + (ord(data[p+2])<<16) + (ord(data[p+3])<<24)); a &= 0xffffffff
        b += (ord(data[p+4]) + (ord(data[p+5])<<8) + (ord(data[p+6])<<16) + (ord(data[p+7])<<24)); b &= 0xffffffff
        c += (ord(data[p+8]) + (ord(data[p+9])<<8) + (ord(data[p+10])<<16) + (ord(data[p+11])<<24)); c &= 0xffffffff
        a, b, c = mix(a, b, c)
        p += 12
        lenpos -= 12

    if lenpos == 12: c += (ord(data[p+8]) + (ord(data[p+9])<<8) + (ord(data[p+10])<<16) + (ord(data[p+11])<<24)); b += (ord(data[p+4]) + (ord(data[p+5])<<8) + (ord(data[p+6])<<16) + (ord(data[p+7])<<24)); a += (ord(data[p+0]) + (ord(data[p+1])<<8) + (ord(data[p+2])<<16) + (ord(data[p+3])<<24));
    if lenpos == 11: c += (ord(data[p+8]) + (ord(data[p+9])<<8) + (ord(data[p+10])<<16)); b += (ord(data[p+4]) + (ord(data[p+5])<<8) + (ord(data[p+6])<<16) + (ord(data[p+7])<<24)); a += (ord(data[p+0]) + (ord(data[p+1])<<8) + (ord(data[p+2])<<16) + (ord(data[p+3])<<24));
    if lenpos == 10: c += (ord(data[p+8]) + (ord(data[p+9])<<8)); b += (ord(data[p+4]) + (ord(data[p+5])<<8) + (ord(data[p+6])<<16) + (ord(data[p+7])<<24)); a += (ord(data[p+0]) + (ord(data[p+1])<<8) + (ord(data[p+2])<<16) + (ord(data[p+3])<<24));
    if lenpos == 9:  c += (ord(data[p+8])); b += (ord(data[p+4]) + (ord(data[p+5])<<8) + (ord(data[p+6])<<16) + (ord(data[p+7])<<24)); a += (ord(data[p+0]) + (ord(data[p+1])<<8) + (ord(data[p+2])<<16) + (ord(data[p+3])<<24));
    if lenpos == 8:  b += (ord(data[p+4]) + (ord(data[p+5])<<8) + (ord(data[p+6])<<16) + (ord(data[p+7])<<24)); a += (ord(data[p+0]) + (ord(data[p+1])<<8) + (ord(data[p+2])<<16) + (ord(data[p+3])<<24));
    if lenpos == 7:  b += (ord(data[p+4]) + (ord(data[p+5])<<8) + (ord(data[p+6])<<16)); a += (ord(data[p+0]) + (ord(data[p+1])<<8) + (ord(data[p+2])<<16) + (ord(data[p+3])<<24));
    if lenpos == 6:  b += ((ord(data[p+5])<<8) + ord(data[p+4])); a += (ord(data[p+0]) + (ord(data[p+1])<<8) + (ord(data[p+2])<<16) + (ord(data[p+3])<<24))
    if lenpos == 5:  b += (ord(data[p+4])); a += (ord(data[p+0]) + (ord(data[p+1])<<8) + (ord(data[p+2])<<16) + (ord(data[p+3])<<24));
    if lenpos == 4:  a += (ord(data[p+0]) + (ord(data[p+1])<<8) + (ord(data[p+2])<<16) + (ord(data[p+3])<<24))
    if lenpos == 3:  a += (ord(data[p+0]) + (ord(data[p+1])<<8) + (ord(data[p+2])<<16))
    if lenpos == 2:  a += (ord(data[p+0]) + (ord(data[p+1])<<8))
    if lenpos == 1:  a += ord(data[p+0])
    a &= 0xffffffff; b &= 0xffffffff; c &= 0xffffffff
    if lenpos == 0: return c, b

    a, b, c = final(a, b, c)

    return c, b

def __hashlittle2_rot(x,k):
    return (x << k) | (x >> (32-k))

def __hashlittle2_mix(a,b,c):
    a -= c;  a ^= __hashlittle2_rot(c, 4);  c += b
    b -= a;  b ^= __hashlittle2_rot(a, 6);  a += c 
    c -= b;  c ^= __hashlittle2_rot(b, 8);  b += a 
    a -= c;  a ^= __hashlittle2_rot(c,16);  c += b 
    b -= a;  b ^= __hashlittle2_rot(a,19);  a += c 
    c -= b;  c ^= __hashlittle2_rot(b, 4);  b += a

    return a,b,c

def hashlittle2_my(key:bytes):
    a=b=c=0xdeadbeef+len(key)

    klen = len(key)
    koffset = 0

    while klen>12:
        a=int.from_bytes(key[koffset:koffset+3],byteorder="big")
        b=int.from_bytes(key[koffset+4:koffset+7],byteorder="big")
        c=int.from_bytes(key[koffset+8:koffset+11],byteorder="big")
        a,b,c = __hashlittle2_mix(a,b,c)
        klen -= 12
        koffset += 12



    return 0

def prefix_hash(s):
    return f"{s[:2]}/{s[2:4]}/{s}"

def have_cached(url,cache_dur=CACHE_DURATION):
    cache_file = os.path.join(CACHE_DIRECTORY,f"{hashlib.sha256(url.encode('utf-8')).hexdigest()}.cache")
    if os.path.exists(cache_file):
        with open(cache_file,"rb") as f:
            ctime = int.from_bytes(f.read(4),byteorder="little")
            return ctime<time()+cache_dur or cache_dur == -1
    else:
        return False

def get_cached(url,cache=True,cache_dur=CACHE_DURATION,max_size=-1,offset=0,size=-1):
    cache_file = os.path.join(CACHE_DIRECTORY,f"{hashlib.sha256(url.encode('utf-8')).hexdigest()}.cache")
    # print(cache_file)
    d = None

    if os.path.exists(cache_file):
        with open(cache_file,"rb",buffering=0) as f:
            ctime = int.from_bytes(f.read(4),byteorder="little")
            if ctime<time()+cache_dur or cache_dur == -1:
                f.seek(offset,1)
                d = f.read(size)

    if d is None:
        buf=BytesIO()
        headers={}
        if not os.path.exists(CACHE_DIRECTORY):
            os.makedirs(CACHE_DIRECTORY)
        with open(cache_file,"wb+") as f:
            f.write(int(time()).to_bytes(4,byteorder="little"))
            with requests.get(url, headers=headers, stream=True) as r:
                r.raise_for_status()
                for x in r.iter_content(512):
                    buf.write(x)
                    f.write(x)
        buf.seek(offset)
        d = buf.read(size)

    try:
        return d.decode("utf-8")
    except:
        return d

# I don't really want to use this, since splitting it into different handlers allows easier 
#  parsing of each subgroup (since the subgroups are quite similar)
def get_cdn_url(cdn_url,cdn_path,file_type,file_hash,index=False):
    return f"http://{cdn_url}/{cdn_path}/{file_type}/{file_hash[:2]}/{file_hash[2:4]}/{file_hash}"+(".index" if index else "")

def _get_cdn_file(cdn_url,cdn_path,file_type,file_hash,cache=True,cache_dur=CACHE_DURATION,max_size=-1,index=False,offset=0,size=-1):
    """ Get a specified file from a CDN for a product."""
    if not file_type in ['data','config','patch']:
        raise Exception(f"Invalid file type {file_type}")
    u=get_cdn_url(cdn_url,cdn_path,file_type,file_hash,index=index)
    return get_cached(u,cache=cache,cache_dur=cache_dur,max_size=max_size,offset=offset,size=size)

def get_cdn_data(cdn_url,cdn_path,file_hash,cache=True,cache_dur=CACHE_DURATION,max_size=-1,index=False, offset=0, size=-1):
    """ Gets a specified data file from the specified cdn """
    return _get_cdn_file(cdn_url,cdn_path,'data',file_hash,cache,cache_dur,max_size=max_size,index=index, offset=offset, size=size)

def get_cdn_config(cdn_url,cdn_path,file_hash,parse=True,cache=True,cache_dur=CACHE_DURATION,max_size=-1,index=False):
    """ Gets specified config from the specified cdn """
    f = _get_cdn_file(cdn_url,cdn_path,'config',file_hash,cache,cache_dur,max_size=max_size,index=index)
    return parse_config(f) if parse else f