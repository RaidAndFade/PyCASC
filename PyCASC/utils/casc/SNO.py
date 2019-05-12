from io import BytesIO
import struct
import pathlib
from PyCASC.utils.CASCUtils import read_cstr

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
