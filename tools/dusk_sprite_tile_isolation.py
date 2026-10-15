"""Isolate shared OAM title tiles for safe per-state translations.

Dusk main Digivice buttons have four NCER 64x64 cells referencing overlapping
ranges of their 4bpp NCGR characters. Text edits across those shared ranges
produce duplicate labels outside the button. Allocate a private character
range for every state and rewrite each NCER tile reference before editing.
"""
import struct
from nitro_bg_preview import graphics,chunk
from probe_dusk_sprite_cells import get_cell_groups,SIZES

def isolate_selected_cells(ncgr:bytes,ncer:bytes,edits:list[dict]):
    work=bytearray(ncgr); cell=bytearray(ncer)
    depth,original_chars=graphics(work)
    if depth!=3:raise ValueError("cannot isolate non-4bpp sprite artwork")
    if len(original_chars)%32:raise ValueError("malformed tile count")
    old_count=len(original_chars)//32
    groups,mode=get_cell_groups(cell)
    selected=sorted(set(e.get("cell",0) for e in edits if "region" in e))
    if not selected:return ncgr,ncer
    at,size=chunk(cell,b"RECN",b"KBEC")
    entries=struct.unpack_from("<H",cell,at+8)[0]
    entry_mode=struct.unpack_from("<H",cell,at+10)[0]
    offsets=struct.unpack_from("<I",cell,at+12)[0]
    table=at+8+offsets
    entry_size=16 if entry_mode else 8
    objbase=table+entries*entry_size
    appended=bytearray()
    for idx in selected:
        if not isinstance(idx,int) or not 0<=idx<len(groups):raise ValueError("bad OAM cell ID")
        if len(groups[idx])!=1:raise ValueError("multi-object tile isolation needs own atlas")
        a0,a1,a2=groups[idx][0]
        shape=a0>>14&3
        sz=a1>>14&3
        if shape>=3 or SIZES[shape][sz]!=(64,64):
            raise ValueError("only original Digivice 64x64 OAM objects supported")
        original_tile=a2&1023
        if original_tile+64>old_count:raise ValueError("original tile mapping outside NCGR")
        dest_index=old_count+len(appended)//32
        if dest_index+64>1024:raise ValueError("OAM 10-bit tile index overflow")
        appended.extend(original_chars[original_tile*32:(original_tile+64)*32])
        rel=struct.unpack_from("<I",cell,table+idx*entry_size+4)[0]
        attr2_offset=objbase+rel+4
        if attr2_offset+2>at+size:raise ValueError("NCER OAM reference outside cell bank")
        old=struct.unpack_from("<H",cell,attr2_offset)[0]
        if old!=a2:raise ValueError("unexpected OAM attribute encoding")
        struct.pack_into("<H",cell,attr2_offset,(old&~1023)|dest_index)
        print("OAM_TILE_ISOLATION",idx,"from",original_tile,"to",dest_index)
    # These Dusk resources are single-chunk Nitro files; do not move a second
    # chunk or disturb other pointers. Fail closed for unsupported layouts.
    char_at,char_len=chunk(work,b"RGCN",b"RAHC")
    data_start=char_at+32
    if data_start+len(original_chars)!=len(work):
        raise ValueError("cannot append characters to multi-section NCGR")
    work.extend(appended)
    struct.pack_into("<I",work,8,len(work))
    struct.pack_into("<I",work,char_at+4,char_len+len(appended))
    struct.pack_into("<I",work,char_at+24,len(original_chars)+len(appended))
    next_depth,next_chars=graphics(work)
    if next_depth!=depth or len(next_chars)!=len(original_chars)+len(appended):
        raise ValueError("NCGR isolation failed structural roundtrip")
    corrected,_=get_cell_groups(cell)
    for idx in selected:
        newtile=corrected[idx][0][2]&1023
        if newtile<old_count:raise ValueError("NCER reference not relocated")
    return bytes(work),bytes(cell)
