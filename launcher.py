import requests
import json
from utils.blizzutils import parse_config, parse_build_config, get_cdn_config, get_cdn_data

#TODO cache these two
def getCatalogCDNs():
    return parse_config(requests.get("http://us.patch.battle.net:1119/catalogs/cdns").text)
def getCatalogVersions():
    return parse_config(requests.get("http://us.patch.battle.net:1119/catalogs/versions").text)

def getCatalog(region="us",version=None,product=None,versions=None):
    """ Get information about a `product` in a catalog `version` in a region. Gets all products on latest version if not specified. 
    Raises Exceptions if any of region, version, or product are invalid."""
    cdns = getCatalogCDNs()
    r_cdn = [cdn for cdn in cdns if cdn['Name']==region]
    print([cdn for cdn in cdns if cdn['Name']=="us"])
    if len(r_cdn):
        r_cdn=r_cdn[0]
    else:
        raise Exception(f"Region {region} is invalid")

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
    
    cdnurl = r_cdn['Hosts'].split(" ")[0]
    cdnpath = r_cdn['Path']
    bc_hash = r_vrn['BuildConfig']
    bc_data = parse_build_config(get_cdn_config(cdnurl,cdnpath,bc_hash,parse=False,cache_dur=3600*6))
    root_hash = bc_data['root']
    root_data = json.loads(get_cdn_data(cdnurl,cdnpath,root_hash))
    # Here we have a list of all CDN'd builds, that we can easily download. pretty cool.
    # if 
    



getCatalog(product="world_of_warcraft")