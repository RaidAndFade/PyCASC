import os
import struct
from blizzutils import var_int,jenkins_hash,parse_build_config,parse_config,prefix_hash,hexkey_to_bytes,byteskey_to_hex
from CASCUtils import parse_encoding_file,parse_root_file,r_cascfile,cascfile_size, NAMED_FILE,SNO_FILE,SNO_INDEXED_FILE

#TODO
# - make all the tables hex -> hex, instead of the current clusterfuck

# methods of reducing memory usage
# lossless:
# - convert hex strs to ints
# lossy
# - only store the first ekey in ckey->ekey table

def prep_listfile(fp):
    names={}
    with open(fp,"r") as f:
        for x in f.readlines():
            x=x.strip()
            names[jenkins_hash(x)]=x
    return names

class FileInfo:
    data_file:int
    offset:int
    compressed_size:int
    uncompressed_size:int
    chunk_count:int
    name:str
    
def r_idx(fp):
    ents={}
    with open(fp,'rb') as f:
        hl,hh,u_0,bi,u_1,ess,eos,eks,afhb,atsm,_,elen,eh=struct.unpack("IIH6BQQII",f.read(0x28))
        esize = ess+eos+eks
        for x in range(0x28,0x28+elen,esize):
            ek=var_int(f,eks,False)
            eo=var_int(f,eos,False)
            es=var_int(f,ess)
            e=FileInfo()
            e.data_file=eo>>30
            e.offset=eo&0x3fffffff
            e.compressed_size=es
            ents[ek]=e
    return ents

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
        inst_hash1,_ = build_config['install'].split()
        download_hash1,_ = build_config['download'].split()
        size_hash1,_ = build_config['size'].split()

        self.file_table = {} # maps ekey -> fileinfo (size, datafile, offset)
        files = os.listdir(self.data_path)
        for x in files:
            if x[-4:]==".idx":
                # i,v=x[:2],x[2:-4]
                ents=r_idx(self.data_path+x)
                for ek in ents:
                    self.file_table[ek]=ents[ek]

        print(f"[ETBL] {len(self.file_table)}")

        enc_info = self.file_table[int(enc_hash2[:18],16)]
        enc_file = r_cascfile(self.data_path,enc_info.data_file,enc_info.offset)
        # Load the CKEY MAP from the encoding file.
        self.ckey_map = parse_encoding_file(enc_file) # maps ckey -> ekey

        for x in self.ckey_map:
            self.ckey_map[x] = int(self.ckey_map[x][:18],16)

        print(f"[CTBL] {len(self.ckey_map)}")

        root_ekey = self.ckey_map[root_ckey]
        root_info = self.file_table[root_ekey]
        root_file = r_cascfile(self.data_path,root_info.data_file,root_info.offset)

        self.file_translate_table = parse_root_file(self.uid,root_file,self) # maps some ID(can be filedataid, path, whatever) -> ckey
        print(f"[FTTBL] {len(self.file_translate_table)}")

        self.file_translate_table.append((NAMED_FILE,"_ROOT",root_ckey))
        
        self.ckey_map[enc_hash1] = int(enc_hash2[:18],16) # map the encoding file's ckey to its own ekey on the ckey-ekey map, since it appears to not be included in the enc-table
        self.file_translate_table.append((NAMED_FILE,"_ENCODING",enc_hash1))
        self.file_translate_table.append((NAMED_FILE,"_INSTALL",inst_hash1))
        self.file_translate_table.append((NAMED_FILE,"_DOWNLOAD",download_hash1))
        self.file_translate_table.append((NAMED_FILE,"_SIZE",size_hash1))

        for x in self.file_translate_table:
            if x[0] is NAMED_FILE:
                ckey=x[2]
                if self.ckey_map[ckey] in self.file_table:
                    self.get_file_info_by_ckey(x[2]).name=x[1]

    def get_name(self,ckey):
        fi = self.get_file_info_by_ckey(ckey)
        if fi is not None:
            return fi.name if hasattr(fi,"name") else None
        return None

    def list_files(self):
        """Returns a list of tuples, each tuple of format (FileName, CKey)"""
        files = []
        for x in self.ckey_map:
            first_ekey = self.ckey_map[x]
            if first_ekey in self.file_table: # check if the ckey_map entry is inside the file.
                n=self.get_name(x)
                if n is not None:
                    files.append((n,x))
        return files

    def get_file_size_by_ckey(self,ckey):
        finfo = self.get_file_info_by_ckey(ckey)
        if finfo == None:
            return None
        if not hasattr(finfo,"uncompressed_size") or finfo.uncompressed_size is None:
            finfo.uncompressed_size, finfo.chunk_count = cascfile_size(self.data_path,finfo.data_file,finfo.offset)
        return finfo.uncompressed_size

    def get_chunk_count_by_ckey(self,ckey):
        finfo = self.get_file_info_by_ckey(ckey)
        if finfo == None:
            return None
        if not hasattr(finfo,"chunk_count") or finfo.chunk_count is None:
            finfo.uncompressed_size, finfo.chunk_count = cascfile_size(self.data_path,finfo.data_file,finfo.offset)
        return finfo.chunk_count

    def get_file_info_by_ckey(self,ckey):
        try:
            return self.file_table[self.ckey_map[ckey]]
        except:
            return None

    def get_file_by_ckey(self,ckey):
        finfo = self.get_file_info_by_ckey(ckey)
        if finfo == None:
            return None
        return r_cascfile(self.data_path,finfo.data_file,finfo.offset)
        

if __name__ == '__main__':
    import cProfile, io
    from pstats import SortKey,Stats
    pr = cProfile.Profile()
    pr.enable()

    # On my pc, these are some paths:
    # cr = CASCReader("G:/Misc Games/Warcraft III") # War 3
    cr = CASCReader("G:/Misc Games/Diablo III") # Diablo 3
    print(f"{len(cr.list_files())} named files loaded in list")
    # On my mac, these are the paths:
    # r("/Users/sepehr/Diablo III") #Diablo 3
    # r("/Applications/Warcraft III") #War3

    pr.disable()
    s = io.StringIO()
    sortby = SortKey.CUMULATIVE
    ps = Stats(pr, stream=s).sort_stats(sortby)
    ps.print_stats()
    print('\n'.join(s.getvalue().split("\n")[:20]))
    import time
    time.sleep(15)