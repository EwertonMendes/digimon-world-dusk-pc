#!/usr/bin/env python3
"""Original-ROM native translated title preview; no game bundle/release."""
import argparse,base64,hashlib,io
from pathlib import Path
from PIL import Image
from probe_dusk_strings import SHA256,files
from probe_dusk_sprite_cells import packed_resource
from dusk_native_title_prompt import replace_title
from probe_dusk_title_prompt_exact import composite_cell

def run(rom):
    if hashlib.sha256(rom).hexdigest()!=SHA256:raise ValueError("wrong ROM")
    fs=files(rom)
    source=packed_resource(rom,fs,"dat/SPR_CHR.PAK",620)
    pal=packed_resource(rom,fs,"dat/SPR_PAL.PAK",620)
    cel=packed_resource(rom,fs,"dat/SPR_CEL.PAK",620)
    target,info=replace_title(source,pal,cel)
    print("TITLE_NATIVE_ORIGINAL_SHA256",hashlib.sha256(source).hexdigest())
    print("TITLE_NATIVE_TRANSLATED_SHA256",hashlib.sha256(target).hexdigest())
    print("TITLE_NATIVE_INFO",info)
    for state in range(4):
        original=composite_cell(source,pal,cel,state)
        translated=composite_cell(target,pal,cel,state)
        im=Image.new("RGB",(192*2,32),(24,26,40))
        im.paste(original,(0,0));im.paste(translated,(192,0))
        im=im.resize((1152,96),Image.Resampling.NEAREST)
        buf=io.BytesIO();im.save(buf,"PNG",optimize=True)
        print("TITLE_NATIVE_FRAME",state)
        print("TITLE_NATIVE_FRAME64 "+base64.b64encode(buf.getvalue()).decode("ascii"))

if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--rom",type=Path,required=True)
    run(parser.parse_args().rom.read_bytes())
