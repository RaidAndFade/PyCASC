import os
import struct
from blizzutils import var_int,jenkins_hash,parse_build_config,parse_config,prefix_hash,hexkey_to_bytes,byteskey_to_hex
from CASCUtils import parse_encoding_file,parse_root_file,r_cascfile,cascfile_size, NAMED_FILE,SNO_FILE,SNO_INDEXED_FILE

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
    with open(fp,'rb') as f:
        hl,hh,u_0,bi,u_1,ess,eos,eks,afhb,atsm,_,elen,eh=struct.unpack("IIH6BQQII",f.read(0x28))
        esize = ess+eos+eks
        for x in range(0x28,0x28+elen,esize):
            ek=var_int(f,eks,False)
            eo=var_int(f,eos,False)
            es=var_int(f,ess)
            e={"datafile":eo>>30,"offset":eo&0x3fffffff,"size":es}
            ents[ek]=e
    return {'entries':ents}

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
        print("[BF]")

        assert build_file is not None and build_config is not None

        self.uid = build_config['build-uid']
        root_ckey = build_config['root']
        enc_hash1,enc_hash2 = build_config['encoding'].split()
        inst_hash1,inst_hash2 = build_config['install'].split()
        download_hash1,download_hash2 = build_config['download'].split()
        size_hash1,size_hash2 = build_config['size'].split()

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
        print(f"[ETBL] {len(ekey_table)}")
        
        self.file_table = ekey_table # lists ekey -> fileinfo

        enc_info = ekey_table[int(enc_hash2[:18],16)]
        enc_file = r_cascfile(self.data_path,enc_info['datafile'],enc_info['offset'],enc_info['size'])
        # Load the CKEY MAP from the encoding file.
        self.ckey_map = parse_encoding_file(enc_file) # maps ckey -> ekey
        print(f"[CTBL] {len(self.ckey_map)}")

        root_ekey = self.ckey_map[root_ckey][0]
        root_info = ekey_table[int(root_ekey[:18],16)]
        root_file = r_cascfile(self.data_path,root_info['datafile'],root_info['offset'],root_info['size'])

        self.file_translate_table = parse_root_file(self.uid,root_file,self) # maps some ID(can be filedataid, path, whatever) -> ckey
        print(f"[FTTBL] {len(self.file_translate_table)}")

        self.file_translate_table.append((NAMED_FILE,"_ROOT",root_ckey))
        self.file_translate_table.append((NAMED_FILE,"_ENCODING",enc_hash1))
        self.file_translate_table.append((NAMED_FILE,"_INSTALL",inst_hash1))
        self.file_translate_table.append((NAMED_FILE,"_DOWNLOAD",download_hash1))
        self.file_translate_table.append((NAMED_FILE,"_SIZE",size_hash1))

        self.ckey_to_name = {}
        for x in self.file_translate_table:
            if x[0] is NAMED_FILE:
                self.ckey_to_name[x[2]] = x[1]
        print(f"[CNTBL] {len(self.ckey_to_name)}")

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

    def get_file_size_by_ckey(self,ckey):
        finfo = self.get_file_info_by_ckey(ckey)
        if finfo == None:
            return None
        return cascfile_size(self.data_path,finfo['datafile'],finfo['offset'],finfo['size'])

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
    import cProfile, io
    from pstats import SortKey,Stats
    pr = cProfile.Profile()
    pr.enable()

    # On my pc, these are some paths:
    cr = CASCReader("G:/Misc Games/Warcraft III") # War 3
    # cr = CASCReader("G:/Misc Games/Diablo III") # Diablo 3
    print(len(cr.list_files()))
    # On my mac, these are the paths:
    # r("/Users/sepehr/Diablo III") #Diablo 3
    # r("/Applications/Warcraft III") #War3

    pr.disable()
    s = io.StringIO()
    sortby = SortKey.CUMULATIVE
    ps = Stats(pr, stream=s).sort_stats(sortby)
    ps.print_stats()
    print(s.getvalue())