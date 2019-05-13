from io import BytesIO
import struct
import pathlib
from PyCASC.utils.CASCUtils import read_cstr, NAMED_FILE, SNO_FILE, SNO_INDEXED_FILE
from PyCASC.utils.blizzutils import byteskey_to_hex

SNOGroups={
    # id : ( name , ext )
    -2:("Code",""),
    -1:("None",""),
    1:("Actor","acr"),
    2:("Adventure","adv"),
    3:("AiBehavior",""),
    4:("AiState",""),
    5:("AmbientSound","ams"),
    6:("Anim","ani"),
    7:("Animation2D","an2"),
    8:("AnimSet","ans"),
    9:("Appearance","app"),
    10:("Hero",""),
    11:("Cloth","clt"),
    12:("Conversation","cnv"),
    13:("ConversationList",""),
    14:("EffectGroup","efg"),
    15:("Encounter","enc"),
    17:("Explosion","xpl"),
    18:("FlagSet",""),
    19:("Font","fnt"),
    20:("GameBalance","gam"),
    21:("Globals","glo"),
    22:("LevelArea","lvl"),
    23:("Light","lit"),
    24:("MarkerSet","mrk"),
    25:("Monster","mon"),
    26:("Observer","obs"),
    27:("Particle","prt"),
    28:("Physics","phy"),
    29:("Power","pow"),
    31:("Quest","qst"),
    32:("Rope","rop"),
    33:("Scene","scn"),
    34:("SceneGroup","scg"),
    35:("Script",""),
    36:("ShaderMap","shm"),
    37:("Shaders","shd"),
    38:("Shakes","shk"),
    39:("SkillKit","skl"),
    40:("Sound","snd"),
    41:("SoundBank","sbk"),
    42:("StringList","stl"),
    43:("Surface","srf"),
    44:("Textures","tex"),
    45:("Trail","trl"),
    46:("UI","ui"),
    47:("Weather","wth"),
    48:("Worlds","wrl"),
    49:("Recipe","rcp"),
    51:("Condition","cnd"),
    52:("TreasureClass",""),
    53:("Account",""),
    54:("Conductor",""),
    55:("TimedEvent",""),
    56:("Act","act"),
    57:("Material","mat"),
    58:("QuestRange","qsr"),
    59:("Lore","lor"),
    60:("Reverb","rev"),
    61:("PhysMesh","phm"),
    62:("Music","mus"),
    63:("Tutorial","tut"),
    64:("BossEncounter","bos"),
    65:("ControlScheme",""),
    66:("Accolade","aco"),
    67:("AnimTree","ant"),
    68:("Vibration",""),
    69:("DungeonFinder","")
}

def _parse_d3_coretoc(ctfd):
    cf = BytesIO(ctfd)
    group_count = 70 # len(SNOGroups) Yeah i dont fucking know why there's 3 groups
    group_lens = [int.from_bytes(cf.read(4), byteorder='little') for x in range(group_count)]
    group_offsets = [int.from_bytes(cf.read(4), byteorder='little') for x in range(group_count)]
    group_unk_counts = [int.from_bytes(cf.read(4), byteorder='little') for x in range(group_count)]

    snomap = {}

    cf.seek(4,1)
    for gri in range(group_count):
        grln=group_lens[gri]
        if grln <= 0: 
            continue
        gr_offset=group_offsets[gri] + 12*group_count+4 # offset + header
        cf.seek(gr_offset)
        for _ in range(grln):
            grpId, snoId, name_offset = struct.unpack("III",cf.read(12))
            noffset = gr_offset + 12*grln + name_offset # offset+header + group
            
            op=cf.tell()
            cf.seek(noffset)
            name = read_cstr(cf)
            cf.seek(op)

            snomap[snoId] = (name,grpId)+SNOGroups[grpId]

    # snoid : snoinfo
    return snomap

def _parse_d3_packages(pkfd):
    pf = BytesIO(pkfd)
    sig,numnames = struct.unpack("II",pf.read(8))
    assert sig == 0xAABB0002
    name_arr = {}
    for _ in range(numnames):
        p=read_cstr(pf).replace("\\","/")
        p=pathlib.PurePath(p)
        # if p.stem in name_arr:
        #     continue

        name_arr[p.stem]=p.parts[:-1]+(p.stem,p.suffix)
    print(f"Finished reading {len(name_arr)}/{numnames} names at {pf.tell()}")
    return name_arr


def _parse_d3_root_entry(df,t):
    ckey = byteskey_to_hex(df.read(16))
    if t is SNO_FILE or t is SNO_INDEXED_FILE:
        snoid,=struct.unpack("I",df.read(4))
        if t is SNO_INDEXED_FILE:
            findex,=struct.unpack("I",df.read(4))
            return t,(snoid,findex),ckey
        else:
            return t,snoid,ckey
    elif t is NAMED_FILE:
        return t,read_cstr(df),ckey

def parse_d3_root(fd,cr):
    f = BytesIO(fd)
    sig = f.read(4)
    assert sig == b'\xc4\xd0\x07\x80'
    count, = struct.unpack("I",f.read(4))
    final_entries = []
    sno_entries = []
    dirs = []
    for _ in range(count):
        ckey=f.read(16)
        name=read_cstr(f)
        dirs.append((name,ckey))

    for name,ckey in dirs:
        ckey=byteskey_to_hex(ckey)
        final_entries.append((NAMED_FILE,"_ROOTFILES/"+name,ckey))
        dirfile = cr.get_file_by_ckey(ckey)
        if dirfile is None:
            continue
        df = BytesIO(dirfile)
        dfmagic = df.read(4)

        snocount, = struct.unpack("I",df.read(4))
        for _ in range(snocount):
            e = _parse_d3_root_entry(df,SNO_FILE)+(name,)
            sno_entries.append(e)
        
        snoidx_count, = struct.unpack("I",df.read(4))
        for _ in range(snoidx_count):
            e = _parse_d3_root_entry(df,SNO_INDEXED_FILE)+(name,)
            sno_entries.append(e)

        namecount, = struct.unpack("I",df.read(4))
        for _ in range(namecount):
            e = _parse_d3_root_entry(df,NAMED_FILE)+(name,)
            final_entries.append(e) 
            # add them directly to the final entries, since these are basically the final results for this type of entry
    
    coretoc_ckey = [c for c in final_entries if c[1]=="CoreTOC.dat"][0][2]
    sno_table = _parse_d3_coretoc(cr.get_file_by_ckey(coretoc_ckey)) # snid : (name,sngrp,grpnm,grpext)

    packages_ckey = [c for c in final_entries if c[1]=="Data_D3\\PC\\Misc\\Packages.dat"][0][2]
    pkg_table = _parse_d3_packages(cr.get_file_by_ckey(packages_ckey)) # fn : (fpath,fname,fext)

    for sf in sno_entries:
        if sf[0]==SNO_FILE:
            if sf[1] in sno_table: # if this file is in the sno_table, then we know it's name
                sfn = sno_table[sf[1]]
                final_entries.append((NAMED_FILE,f"{sfn[2]}/{sfn[0]}.{sfn[3]}",sf[2]))
            else: # otherwise, we dont know the name.
                final_entries.append((SNO_FILE,sf[1],sf[2]))
        else: # sf is SNO_INDEXED_FILE
            if sf[1][0] in sno_table: # if this file is in the sno_table, then we know it's name
                sfn = sno_table[sf[1][0]]
                pkg = pkg_table[sfn[0]]
                final_entries.append((NAMED_FILE,f"{sfn[2]}/{pkg[1]}/{sf[1][1]:05d}{pkg[-1]}",sf[2]))
            else: # otherwise, we dont know the name.
                final_entries.append((SNO_INDEXED_FILE,sf[1],sf[2]))

    return final_entries
