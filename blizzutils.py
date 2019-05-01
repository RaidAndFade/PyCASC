from typing import Dict,List
import requests
import os
import hashlib
import pickle
from time import time

CACHE_DURATION = 3600 # one hour

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
    b=b''
    for x in zip(s[0::2], s[1::2]):
        b+=bytes([int(x[0]+x[1],16)])
    return b
def byteskey_to_hex(b:bytes):
    s=""
    for x in b:
        s+=f"{x:02x}"
    return s
    
def var_int(f:object,l:int,le=True):
    o=f.read(l)
    i=0
    if le:
        i=int.from_bytes(o, byteorder='little', signed=False)
    else:
        i=int.from_bytes(o, byteorder='big', signed=False)
    return i

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

# I don't really want to use this, since splitting it into different handlers allows easier 
#  parsing of each subgroup (since the subgroups are quite similar)
def _get_cdn_file(cdn_url,cdn_path,file_type,file_hash,ssl=False,cache=True,cache_dur=CACHE_DURATION):
    """ Get a specified file from a CDN for a product."""
    if not file_type in ['data','config','patch']:
        raise Exception(f"Invalid file type {file_type}")
    u=f"http://{cdn_url}/{cdn_path}/{file_type}/{file_hash[:2]}/{file_hash[2:4]}/{file_hash}"
    cache_file = f"cache/{hashlib.sha256(u.encode('utf-8')).hexdigest()}.cache"
    if cache and os.path.exists(cache_file):
        with open(cache_file,"rb") as f:
            d = pickle.load(f)
            print(d['data'])
            if d['time']<time()+cache_dur:
                return d['data']
    r = requests.get(u).text
    if cache:
        if not os.path.exists("cache"):
            os.makedirs("cache")
        with open(cache_file,"wb+") as f:
            pickle.dump({'time':time(),'data':r},f)
    return r

def get_cdn_data(cdn_url,cdn_path,file_hash,ssl=False,cache=True,cache_dur=CACHE_DURATION):
    """ Gets a specified data file from the specified cdn """
    return _get_cdn_file(cdn_url,cdn_path,'data',file_hash,ssl,cache,cache_dur)

def get_cdn_config(cdn_url,cdn_path,file_hash,ssl=False,parse=True,cache=True,cache_dur=CACHE_DURATION):
    """ Gets specified config from the specified cdn """
    f = _get_cdn_file(cdn_url,cdn_path,'config',file_hash,ssl,cache,cache_dur)
    return parse_config(f) if parse else f