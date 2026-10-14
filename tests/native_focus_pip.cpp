#include "dusk_native_ui.h"
#include <cassert>
#include <cmath>
#include <iostream>
int main() {
  using namespace dusk_native;
  long total=0;
  for(int w : {320,360,480,640,720,800,1280,1360,1920,2560,3440})
  for(int h : {240,320,360,480,600,720,768,1080,1440})
  for(int primary=0;primary<2;++primary)
  for(int aux=0;aux<2;++aux)
  for(int ratio=0;ratio<2;++ratio)
  for(int size : {25,36,50,65})
  for(int corner=0;corner<4;++corner) {
    Config c{};c.layout=Layout::Focus;c.focus_top=primary;c.auxiliary=aux;
    c.fill_wide=ratio;c.float_percent=size;c.float_corner=corner;
    const auto g=compute(w,h,c);
    auto inside=[&](Rect r){return r.w>0 && r.h>0 && r.x>=0 && r.y>=0 && r.x+r.w<=std::max(w,320) && r.y+r.h<=std::max(h,240);};
    const auto major=primary?g.top:g.bottom;
    const auto minor=primary?g.bottom:g.top;
    assert(inside(major));
    assert(std::abs((double)major.w/major.h-(ratio?16./9.:4./3.))<.03);
    if(aux) {
      assert(inside(minor));assert(inside(g.pip_bar));
      assert(!contains(minor,g.pip_bar.x+5,g.pip_bar.y+4));
      assert(g.pip_bar.y+g.pip_bar.h==minor.y);
      assert(g.pip_bar.x==minor.x && g.pip_bar.w==minor.w);
      assert(minor.y+minor.h<=g.play.h-8);
      assert(inside(g.pip_swap));assert(inside(g.pip_minimize));
      if(primary) {
        float tx=-1,ty=-1;
        assert(map_touch(g,minor.x+minor.w*.5f,minor.y+minor.h*.5f,tx,ty));
        assert(std::abs(tx-128.)<1.);assert(std::abs(ty-96.)<1.);
      }
    } else { assert(minor.w==0 && minor.h==0);assert(inside(g.pip_restore)); }
    if(!primary) {
       float tx=-1,ty=-1;
       assert(map_touch(g,major.x+major.w*.5f,major.y+major.h*.5f,tx,ty));
       assert(std::abs(tx-128)<1 && std::abs(ty-96)<1);
    }
    ++total;
  }
  std::cout<<"PASS "<<total<<" focus/PiP variants"<<std::endl;
}
