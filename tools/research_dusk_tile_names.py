from pathlib import Path
import argparse,hashlib
from probe_dusk_strings import SHA256,files
def main(path:Path):
    rom=path.read_bytes()
    if hashlib.sha256(rom).hexdigest()!=SHA256:raise ValueError("wrong ROM")
    f=files(rom)
    for name,(fid,lo,hi) in f.items():
        if name.lower().endswith(".ncgr"):
            print(f"NCGR {fid:5} {hi-lo:8} {name}")
if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--rom",type=Path,required=True)
    x=a.parse_args();main(x.rom)
