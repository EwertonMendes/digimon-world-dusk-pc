"""Audit verified ARM9 native shop action words and writable slot capacities.

Read-only: displays short decoded neighbors around first Buy, Sell and Quit
plus terminator locations. Never applies replacements without byte identity.
"""
import argparse,hashlib
from probe_dusk_strings import SHA256,u32,u16
from research_dusk_menu_strings import enc
from find_dusk_common_text import decode
def main(rom):
    if hashlib.sha256(rom).hexdigest()!=SHA256:raise ValueError("unexpected source game")
    start=u32(rom,0x20);end=start+u32(rom,0x2c)
    for word in ["Buy","Sell","Quit","Money"]:
        raw=enc(word)
        results=[]
        at=rom.find(raw,start,end)
        while at>=0 and len(results)<35:
            if (at-start)%2==0:
                before=[u16(rom,i) for i in range(max(start,at-36),at,2)]
                after=[u16(rom,i) for i in range(at,min(end,at+140),2)]
                stopper=next((i for i,v in enumerate(after) if v in(0xffff,0xfffe,0)),None)
                zeros=0
                if stopper is not None and after[stopper]==0:
                    while stopper+zeros<len(after) and after[stopper+zeros]==0:zeros+=1
                next_start=stopper+zeros if stopper is not None else 0
                results.append({"rom_offset":at,"relative":at-start,
                    "source":word,"before":decode(before),
                    "after":decode(after[:min(stopper or 30,30)]),
                    "end_word":(hex(after[stopper]) if stopper is not None else "none"),
                    "slots_bytes":(stopper*2 if stopper is not None else None),
                    "zero_words_after":zeros,
                    "next_words":[hex(v) for v in after[next_start:next_start+9]]})
            at=rom.find(raw,at+2,end)
        print("LABEL",word,"hits",len(results))
        for row in results[:22]:print("AROUND",row)
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--rom",required=True)
    a=p.parse_args();main(open(a.rom,"rb").read())
