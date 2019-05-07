import requests, json, os, hashlib, pickle
from time import time
from PyCASC.utils.blizzutils import parse_config, parse_build_config, get_cdn_config, get_cdn_data

CACHE_DURATION = 3600 # one hour

def get_cached(url,cache=True,cache_dur=CACHE_DURATION):
    cache_file = f"cache/{hashlib.sha256(url.encode('utf-8')).hexdigest()}.cache"
    if os.path.exists(cache_file):
        with open(cache_file,"rb") as f:
            d = pickle.load(f)
            if d['time']<time()+cache_dur:
                return d['data']
    r = requests.get(url).text
    if not os.path.exists("cache"):
        os.makedirs("cache")
    with open(cache_file,"wb+") as f:
        pickle.dump({'time':time(),'data':r},f)
    return r

def getCatalogCDNs():
    return parse_config(get_cached("http://us.patch.battle.net:1119/catalogs/cdns"))
def getCatalogVersions():
    return parse_config(get_cached("http://us.patch.battle.net:1119/catalogs/versions"))

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

def getCDN(region="us"):
    cdns = getCatalogCDNs()
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
    cdnurl,cdnpath = getCDN(region)
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
    cdnurl, cdnpath = getCDN(region)
    
    data = json.loads(get_cdn_data(cdnurl,cdnpath,prod['hash']))
    if not raw: # do cleanup ourselves
        data = fixStrings(data,locale=locale)
        for x in data['products']:
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