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

def prefix_hash(s):
    return f"{s[:2]}/{s[2:4]}/{s}"

def get_cached(url,cache=True,cache_dur=CACHE_DURATION,max_size=-1):
    cache_file = os.path.join(CACHE_DIRECTORY,f"{hashlib.sha256(url.encode('utf-8')).hexdigest()}.cache")
    if os.path.exists(cache_file):
        with open(cache_file,"rb") as f:
            d = pickle.load(f)
            if d['time']<time()+cache_dur:
                d = d['data']
    else:
        buf=BytesIO()
        rs=0
        headers={}
        with requests.get(url, headers=headers, stream=True) as r:
            r.raise_for_status()
            for x in r.iter_content(512):
                buf.write(x)
                rs+=len(x)
                if max_size>0 and rs>max_size:
                    break
        d = buf.getvalue()
        if not os.path.exists(CACHE_DIRECTORY):
            os.makedirs(CACHE_DIRECTORY)
        with open(cache_file,"wb+") as f:
            pickle.dump({'time':time(),'data':buf.getvalue()},f)
    try:
        return d.decode("utf-8")
    except:
        return d

# I don't really want to use this, since splitting it into different handlers allows easier 
#  parsing of each subgroup (since the subgroups are quite similar)
def _get_cdn_file(cdn_url,cdn_path,file_type,file_hash,cache=True,cache_dur=CACHE_DURATION,max_size=-1,index=False):
    """ Get a specified file from a CDN for a product."""
    if not file_type in ['data','config','patch']:
        raise Exception(f"Invalid file type {file_type}")
    u=f"http://{cdn_url}/{cdn_path}/{file_type}/{file_hash[:2]}/{file_hash[2:4]}/{file_hash}"+(".index" if index else "")
    return get_cached(u,cache=cache,cache_dur=cache_dur,max_size=max_size)

def get_cdn_data(cdn_url,cdn_path,file_hash,cache=True,cache_dur=CACHE_DURATION,max_size=-1,index=False):
    """ Gets a specified data file from the specified cdn """
    return _get_cdn_file(cdn_url,cdn_path,'data',file_hash,cache,cache_dur,max_size=max_size,index=index)

def get_cdn_config(cdn_url,cdn_path,file_hash,parse=True,cache=True,cache_dur=CACHE_DURATION,max_size=-1,index=False):
    """ Gets specified config from the specified cdn """
    f = _get_cdn_file(cdn_url,cdn_path,'config',file_hash,cache,cache_dur,max_size=max_size,index=index)
    return parse_config(f) if parse else f