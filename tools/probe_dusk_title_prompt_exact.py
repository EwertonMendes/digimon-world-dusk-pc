#!/usr/bin/env python3
"""Render true 1D-128 native title prompt cells, not legacy no-stride atlas."""
from __future__ import annotations
import argparse,hashlib,base64,io
from pathlib import Path
from PIL import Image
from probe_dusk_strings import SHA256,files
from probe_dusk_sprite_cells import packed_resource,get_cell_groups
from dusk_sprite_inplace_editor import extract_cell
from nitro_bg_preview import palette
def run(raw):
    if hashlib.sha256(raw).hexdigest()!=SHA256:raise ValueError("wrong exact ROM")
    fs=files(raw)
    for sid in (620,625,626):
        ch=packed_resource(raw,fs,"dat/SPR_CHR.PAK",sid)
        cl=packed_resource(raw,fs,"dat/SPR_CEL.PAK",sid)
        pl=packed_resource(raw,fs,"dat/SPR_PAL.PAK",sid)
        states,mode=get_cell_groups(cl)
        print("TITLE_EXACT_ID",sid,"states",len(states),"mode",mode,"palette",[(i,p[:3]) for i,p in enumerate(palette(pl)[:16])])
        for i in range(min(len(states),8)):
            print("TITLE_EXACT_OAM",sid,i,states[i])
            view=extract_cell(ch,pl,cl,i)
            print("TITLE_EXACT_SIZE",sid,i,view.size)
            pic=view.image.resize((view.size[0]*3,view.size[1]*3),Image.Resampling.NEAREST)
            buf=io.BytesIO();pic.save(buf,"PNG",optimize=True)
            print("TITLE_EXACT_FRAME",sid,i)
            print("TITLE_EXACT_FRAME64 "+base64.b64encode(buf.getvalue()).decode())
if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("--rom",type=Path,required=True)
    run(ap.parse_args().rom.read_bytes())
