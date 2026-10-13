// ROM-free exhaustive native SDL3 geometry smoke: included from patched upstream.
#include "dusk_native_ui.h"
#include <cassert>
#include <cmath>
#include <iostream>
int main() {
  using namespace dusk_native;
  int checked=0;
  for(int w: {320,360,600,800,1280,1920,3440})
    for(int h: {240,360,600,900,1080,1440})
      for(int mode=0;mode<5;++mode)
        for(int rev=0;rev<2;++rev)
          for(int aux=0;aux<2;++aux) {
            Config c{};
            c.layout=Layout(mode); c.reversed=bool(rev); c.auxiliary=bool(aux);
            const Geometry g=compute(w,h,c);
            auto inside=[&](Rect r) {
              return r.x>=0&&r.y>=0&&r.w>0&&r.h>0&&r.x+r.w<=w&&r.y+r.h<=h;
            };
            assert(inside(g.bottom));
            if(aux && mode!=int(Layout::MainOnly)) assert(inside(g.top));
            else assert(g.top.w==0);
            float x=0,y=0;
            assert(map_touch(g,g.bottom.x+g.bottom.w*.5f,
                               g.bottom.y+g.bottom.h*.5f,x,y));
            assert(std::abs(x-128.f)<1.1f&&std::abs(y-96.f)<1.1f);
            if(inside(g.top) && mode!=int(Layout::Floating)) {
              assert(g.top.x+g.top.w<=g.bottom.x||g.bottom.x+g.bottom.w<=g.top.x||
                     g.top.y+g.top.h<=g.bottom.y||g.bottom.y+g.bottom.h<=g.top.y);
              assert(!map_touch(g,g.top.x+g.top.w*.5f,
                                  g.top.y+g.top.h*.5f,x,y));
            }
            if((mode==int(Layout::Modern)||mode==int(Layout::Horizontal))&&aux)
              assert((g.bottom.x<g.top.x)!=bool(rev));
            if(mode==int(Layout::Classic)&&aux)
              assert((g.bottom.y>g.top.y)!=bool(rev));
            ++checked;
          }
  std::cout<<"PASS "<<checked<<" screen placement and touchscreen cases\n";
}
