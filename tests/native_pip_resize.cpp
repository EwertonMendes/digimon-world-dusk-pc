#include "dusk_native_ui.h"
#include <cassert>
#include <cmath>
#include <iostream>
int main() {
 using namespace dusk_native;
 long count=0;
 for(int w:{320,640,1024,1366,1920,2560})
 for(int h:{240,480,720,1080,1440})
 for(bool top:{false,true})
 for(int corner=0;corner<4;++corner)
 for(int p:{25,36,50,65}) {
  Config c{};c.layout=Layout::Focus;c.focus_top=top;c.float_percent=p;
  c.float_corner=corner;
  auto g=compute(w,h,c);
  Rect pip=focus_pip(g,c);
  assert(pip.w>0 && pip.h>0);
  // All four border grips are active and preserve aspect.
  for(auto [x,y,mask] : {
   std::tuple<float,float,int>{pip.x+1.f,pip.y+pip.h*.5f,EdgeLeft},
   std::tuple<float,float,int>{pip.x+pip.w-1.f,pip.y+pip.h*.6f,EdgeRight},
   std::tuple<float,float,int>{pip.x+pip.w*.25f,g.pip_bar.y+1.f,EdgeTop},
   std::tuple<float,float,int>{pip.x+pip.w*.25f,pip.y+pip.h-1.f,EdgeBottom},
   std::tuple<float,float,int>{pip.x+1.f,pip.y+pip.h-1.f,EdgeLeft|EdgeBottom},
   std::tuple<float,float,int>{pip.x+pip.w-1.f,pip.y+pip.h-1.f,EdgeRight|EdgeBottom}
  }) {
   int edges=pip_resize_edges(g,c,x,y);
   assert(edges&mask);
   auto result=resize_pip(g.play,pip,edges,20.f,15.f,c.float_percent);
   assert(result.percent>=25 && result.percent<=65);
   assert(result.rect.w>0 && result.rect.h>0);
   assert(std::abs(result.rect.w*3-result.rect.h*4)<4);
   assert(result.rect.x>=0 && result.rect.y>=0);
   assert(result.rect.x+result.rect.w<=g.play.w);
   assert(result.rect.y+result.rect.h<=g.play.h-12);
   ++count;
  }
  // Center click is gameplay, not a resize.
  assert(pip_resize_edges(g,c,pip.x+pip.w*.5f,pip.y+pip.h*.5f)==EdgeNone);
  // Header action targets retain click priority.
  assert(pip_resize_edges(g,c,g.pip_swap.x+g.pip_swap.w*.5f,g.pip_swap.y+8)==EdgeNone);
  c.auxiliary=false;
  assert(pip_resize_edges(compute(w,h,c),c,pip.x+1,pip.y+1)==EdgeNone);
 }
 std::cout<<"PASS "<<count<<" focus PiP border/corner resizing checks\n";
}
