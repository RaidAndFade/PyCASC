import requests, json, os, hashlib, pickle
from time import time
from io import BytesIO
from PyCASC import CACHE_DURATION
from PyCASC.utils.blizzutils import parse_config, parse_build_config, get_cdn_config, get_cdn_data, get_cached, have_cached, get_cdn_url

memcache = {}

def get_mem_cached(url,cache_dur=CACHE_DURATION):
    if url in memcache:
        return memcache[url]
    else:
        dat = get_cached(url,cache_dur)
        memcache[url] = dat
        return dat
        

def getProductCDNs(product):
    return parse_config(get_mem_cached(f"http://us.patch.battle.net:1119/{product}/cdns", cache_dur=3600*24))
def getProductVersions(product):
    return parse_config(get_cached(f"http://us.patch.battle.net:1119/{product}/versions", cache_dur=3600*24))
def getProductBlobs(product):
    return parse_config(get_cached(f"http://us.patch.battle.net:1119/{product}/blobs", cache_dur=3600*24))
def getProductInstallBlob(product):
    return get_cached(f"http://us.patch.battle.net:1119/{product}/blob/install", cache_dur=3600*24)
def getProductGameBlob(product):
    return get_cached(f"http://us.patch.battle.net:1119/{product}/blob/game", cache_dur=3600*24)

def getProductCDNFile(product,file_hash,region="us",ftype="data",cache_dur=CACHE_DURATION,enc=None,max_size=-1,index=False,offset=0,size=-1):
    cdnurl,cdnpath = getCDN(product,region)
    if ftype == "config":
        d = get_cdn_config(cdnurl,cdnpath,file_hash,parse=False,cache_dur=cache_dur,max_size=max_size, index=index)
    else:
        d = get_cdn_data(cdnurl,cdnpath,file_hash,cache_dur=cache_dur,max_size=max_size, index=index, offset=offset, size=size)
    return d

def isCDNFileCached(product,file_hash,region="us",ftype="data",cache_dur=CACHE_DURATION,enc=None,max_size=-1,index=False):
    cdnurl,cdnpath = getCDN(product,region)
    return have_cached(get_cdn_url(cdnurl,cdnpath,ftype,file_hash,index=index),cache_dur=CACHE_DURATION)

def getCatalogCDNs():
    return parse_config(get_cached("http://us.patch.battle.net:1119/catalogs/cdns", cache_dur=3600*24))
def getCatalogVersions():
    return parse_config(get_cached("http://us.patch.battle.net:1119/catalogs/versions", cache_dur=3600*24))

def fixStrings(data,locale="enUS",validStrings=None):
    """ Replace all instances of locale strings with the locale provided, validStrings must be None in non-recursive steps
    """
    if validStrings is None:
        validStrings = data['strings']['default']
        validStrings.update(data['files']['default'])
        if locale in data['strings']:
            validStrings.update(data['strings'][locale])
        if locale in data['files']:
            validStrings.update(data['files'][locale])

    out={} if isinstance(data,dict) else [None]*len(data) 
    for x in (data if isinstance(data,dict) else range(len(data))):
        if x == "strings" or x == "files": 
            out[x]=data[x]
            continue
        k = validStrings[x] if x in validStrings else x
        if isinstance(data[x],dict) or isinstance(data[x],list) or isinstance(data[x],tuple):
            out[k]=fixStrings(data[x],validStrings=validStrings)
        else:
            if data[x] in validStrings:
                out[k]=validStrings[data[x]]
            else:
                out[k]=data[x]
    return out

def getCDN(product="catalogs",region="us"):
    cdns = getProductCDNs(product)
    r_cdn = [cdn for cdn in cdns if cdn['Name']==region]
    
    if len(r_cdn):
        r_cdn=r_cdn[0]
    else:
        raise Exception(f"Region {region} is invalid")
    
    cdnurl = r_cdn['Hosts'].split(" ")[0]
    cdnpath = r_cdn['Path']
    return cdnurl,cdnpath

def getVersion(version=None,versions=None):
    if versions == None:
        versions = getCatalogVersions()
    if version == None:
        r_vrn = versions[-1]
    else:
        r_vrn = [vrn for vrn in versions if vrn['VersionsName']==version]
        if len(r_vrn):
            r_vrn=r_vrn[0]
        else:
            raise Exception(f"Version {version} is invalid")
    return r_vrn

def getCatalogRoot(region="us",version=None,versions=None):
    cdnurl,cdnpath = getCDN("catalogs",region)
    r_vrn = getVersion(version,versions)

    bc_hash = r_vrn['BuildConfig']
    bc_data = parse_build_config(get_cdn_config(cdnurl,cdnpath,bc_hash,parse=False,cache_dur=3600*6))
    root_hash = bc_data['root']
    root_data = json.loads(get_cdn_data(cdnurl,cdnpath,root_hash))
    return root_data

def getProductData(product,region="us",version=None,locale="enUS",raw=False):
    r = getCatalogRoot(region,version)
    prods = {r['name']:r for r in r['fragments']}
    
    if product not in prods:
        return None

    prod=prods[product]
    cdnurl, cdnpath = getCDN("catalogs",region)
    
    data = json.loads(get_cdn_data(cdnurl,cdnpath,prod['hash']))
    if not raw: # do cleanup ourselves
        data = fixStrings(data,locale=locale)
        for x in data['products']:
            if 'uid' not in x['base']:
                x['base']['uid'] = product
            x['base']['install']=data['installs'][x['base']['uid']]
            for y in x['base']['types']:
                i=x['base']['types'][y]
                uid = i['uid'] if 'uid' in i else x['base']['uid']
                if uid not in data['installs']:
                    uid = x['base']['uid']
                i['install'] = data['installs'][uid]
        
        #this shit has been used. no longer necessary
        del data['installs']
        del data['files']
        del data['strings']
    return data

if __name__ == '__main__':
    v = getCatalogVersions()
    print(getCatalogRoot(versions=v))