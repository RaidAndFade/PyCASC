import os
import struct
from blizzutils import var_int,jenkins_hash,parse_build_config,parse_config,prefix_hash,hexkey_to_bytes,byteskey_to_hex
from CASCUtils import parse_encoding_file,parse_root_file,r_cascfile

#TODO
# - make all the tables hex -> hex, instead of the current clusterfuck

def prep_listfile(fp):
    names={}
    with open(fp,"r") as f:
        for x in f.readlines():
            x=x.strip()
            names[jenkins_hash(x)]=x
    return names

def r_idx(fp):
    ents={}
    data={'entries':ents}
    # print(fp)
    with open(fp,'rb') as f:
        # shortened forms of https://wowdev.wiki/CASC, i'll make it legible once it works
        hl,hh,u_0,bi,u_1,ess,eos,eks,afhb,atsm,_,elen,eh=struct.unpack("IIH6BQQII",f.read(0x28))
        esize = ess+eos+eks
        encodingfile=(0x5e,0x46,0x1c,0xb3,0xde,0x2c,0x07,0xe8,0x26) #"\x5e\x46\x1c\xb3\xde\x2c\x07\xe8\x26")
        for x in range(0x28,0x28+elen,esize):
            ek=var_int(f,eks,False)
            eo=var_int(f,eos,False)
            es=var_int(f,ess)
            e={"datafile":eo>>30,"offset":eo&0x3fffffff,"size":es}
            ents[ek]=e
        # print(ents)
        # assert len(ents) == elen//esize
    return data

class CASCReader:
    def __init__(self,f):
        if not os.path.exists(f+"/.build.info") or not os.path.exists(f+"/Data/data"):
            raise Exception("Not a valid CASC datapath")
        self.path = f
        self.build_path = f+"/.build.info"
        self.data_path = f+"/Data/data/"

        build_file,build_config=None,None
        with open(self.build_path,"r") as b:
            build_file = parse_config(b.read())[0]
        with open(f+"/Data/config/"+prefix_hash(build_file['Build Key']),"r") as b:
            build_config = parse_build_config(b.read())

        assert build_file is not None and build_config is not None

        root_ckey = build_config['root']
        enc_hash1,enc_hash2 = build_config['encoding'].split()

        indicies = {}
        files = os.listdir(self.data_path)
        for x in files:
            if x[-4:]==".idx":
                i,v=x[:2],x[2:-4]
                indicies[v]=indicies[v] if v in indicies else {}
                indicies[v][i]=r_idx(self.data_path+x)

        ekey_table={}
        for i in indicies:
            i=indicies[i]
            for v in i:
                v=i[v]
                for ek in v['entries']:
                    el=v['entries'][ek]
                    ekey_table[ek]=el
        
        self.file_table = ekey_table # lists ekey -> fileinfo

        enc_info = ekey_table[int(enc_hash2[:18],16)]
        enc_file = r_cascfile(self.data_path,enc_info['datafile'],enc_info['offset'],enc_info['size'])
        # Load the CKEY MAP from the encoding file.
        self.ckey_map = parse_encoding_file(enc_file) # maps ckey -> ekey

        root_ekey = self.ckey_map[root_ckey][0]
        root_info = ekey_table[int(root_ekey[:18],16)]
        root_file = r_cascfile(self.data_path,root_info['datafile'],root_info['offset'],root_info['size'])

        self.file_translate_table = parse_root_file(build_config['build-uid'],root_file) # maps some ID(can be filedataid, path, whatever) -> ckey

        self.ckey_to_name = {}
        for x in self.file_translate_table:
            self.ckey_to_name[x[1]] = x[0]

    def get_name(self,ckey):
        return self.ckey_to_name[ckey] if ckey in self.ckey_to_name else None

    def list_files(self):
        """Returns a list of tuples, each tuple of format (FileName, CKey)"""
        files = []
        for x in self.ckey_map:
            first_ekey = self.ckey_map[x][0]
            if int(first_ekey[:18],16) in self.file_table: # check if the ckey_map entry is inside the file.
                n=self.get_name(x)
                if n is not None:
                    files.append((n,x))
        return files

    def get_file_info_by_ckey(self,ckey):
        try:
            return self.file_table[int(self.ckey_map[ckey][0][:18],16)]
        except:
            return None

    def get_file_by_ckey(self,ckey):
        finfo = self.get_file_info_by_ckey(ckey)
        if finfo == None:
            return None
        return r_cascfile(self.data_path,finfo['datafile'],finfo['offset'],finfo['size'])
        

if __name__ == '__main__':
    # On my pc, these are some paths:
    cr = CASCReader("G:/Misc Games/Warcraft III") #War3
    cr.list_files()
    # r("G:/Misc Games/Diablo III") #Diablo 3

    # On my mac, these are the paths:
    # r("/Users/sepehr/Diablo III") #Diablo 3
    # r("/Applications/Warcraft III") #War3