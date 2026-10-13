#include "dusk_native_ui.h"
#include <cassert>
#include <cmath>
#include <iostream>

int main() {
    using namespace dusk_native;
    int cases=0;
    for (int width : {360, 800, 1280, 1360, 1920, 2560}) {
        for (int height : {260, 600, 768, 1080}) {
            for (int mode=0;mode<5;++mode) {
                for (bool aux : {false,true}) {
                    Config cfg{};
                    cfg.layout=static_cast<Layout>(mode);
                    cfg.auxiliary=aux;
                    auto g=compute(width,height,cfg);
                    assert(g.bottom.w>0 && g.bottom.h>0);
                    assert(g.bottom.x>=0 && g.bottom.y>=0);
                    assert(g.bottom.x+g.bottom.w<=width);
                    assert(g.bottom.y+g.bottom.h<=height);
                    assert(std::abs(g.bottom.w*192-g.bottom.h*256)<=256);
                    if (cfg.layout==Layout::MainOnly || !cfg.auxiliary) {
                        assert(g.top.w==0 && g.top.h==0);
                    } else {
                        assert(g.top.w>0 && g.top.h>0);
                        assert(g.top.x>=0 && g.top.y>=0);
                        assert(g.top.x+g.top.w<=width);
                        assert(g.top.y+g.top.h<=height);
                    }
                    float tx=-1,ty=-1;
                    assert(map_touch(g,g.bottom.x+g.bottom.w/2.f,
                                     g.bottom.y+g.bottom.h/2.f,tx,ty));
                    assert(tx>=0 && tx<256 && ty>=0 && ty<192);
                    assert(!map_touch(g,-1,-1,tx,ty));
                    ++cases;
                }
            }
        }
    }
    // Overlay intentionally receives no touchscreen input in floating mode.
    Config floating{};
    floating.layout=Layout::Floating;
    auto g=compute(1360,800,floating);
    float tx=0,ty=0;
    assert(contains(g.top,g.top.x+2,g.top.y+2));
    assert(!map_touch(g,0,0,tx,ty));
    std::cout<<"Validated "<<cases<<" layouts, aspect ratios and touchscreen mappings\\n";
}
