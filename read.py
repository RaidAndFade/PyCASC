import os
import struct
from blizzutils import var_int

def r_idx(fp):
    ents={}
    data={'entries':ents}
    print(fp)
    with open(fp,'rb') as f:
        # shortened forms of https://wowdev.wiki/CASC, i'll make it legible once it works
        hl,hh,u_0,bi,u_1,ess,eos,eks,afhb,atsm,_,elen,eh=struct.unpack("iihbbbbbbqqii",f.read(0x28))
        esize = ess+eos+eks
        counts = {}
        for x in range(0x28,0x28+elen,esize):
            ek=var_int(f,eks)
            eo=var_int(f,eos)
            es=var_int(f,ess)
            e={"key":ek,"datafile":eo>>30,"offset":eo,"size":es}
            c = 1 if ek not in counts else counts[ek]+1
            ents[str(ek)+":"+str(c)]=e
            counts[ek]=c
        # print(ents)
        print(len(ents),hl,hh,u_0,bi,u_1,ess,eos,eks,afhb,atsm,_,elen,eh,elen//esize)
    return data

def r_data():
    pass

def r(f):
    if not os.path.exists(f+"/data"):
        raise "Not a valid CASC datapath"
    else:
        f=f+"/data/"
    indicies = {}
    files = os.listdir(f)
    for x in files:
        if x[-4:]==".idx":
            i,v=x[:2],x[2:-4]
            indicies[v]=indicies[v] if v in indicies else {}
            indicies[v][i]=r_idx(f+x)
            break
    # print(indicies)

r("/Users/sepehr/Diablo III/Data/") #Diablo 3
# r("/Applications/Warcraft III/Data")