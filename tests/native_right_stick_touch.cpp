#include "dusk_native_ui.h"
#include <cassert>
#include <cmath>
#include <iostream>
#include <limits>
int main() {
    using namespace dusk_native;
    RightStickTouch stick{};
    assert(stick.x==128.f && stick.y==96.f && !stick.down);
    assert(!stick.step(0.12f,0.1f,1.f/60.f,true) && !stick.down);
    const float initial=stick.x;
    for(int i=0;i<60;++i) {
        assert(stick.step(1.f,0.f,1.f/60.f,true));
    }
    assert(stick.x>initial+90.f && stick.x<=255.f);
    float moved=stick.x;
    assert(!stick.step(0.f,0.f,1.f/60.f,true));
    assert(!stick.down && stick.x==moved);
    assert(stick.step(-1.f,-1.f,1.f/30.f,true));
    assert(stick.x<moved && stick.y<96.f);
    assert(!stick.step(1.f,0.f,1.f/60.f,false) && !stick.down);
    for(int i=0;i<240;++i)stick.step(-1.f,1.f,1.f/60.f,true);
    assert(stick.x>=0.f && stick.x<=255.f && stick.y>=0.f && stick.y<=191.f);
    RightStickTouch a{},b{};
    for(int i=0;i<120;++i)a.step(.8f,.2f,1.f/120.f,true);
    for(int i=0;i<60;++i)b.step(.8f,.2f,1.f/60.f,true);
    assert(std::abs(a.x-b.x)<.1f && std::abs(a.y-b.y)<.1f);
    assert(!stick.step(std::numeric_limits<float>::quiet_NaN(),0.f,.016f,true) && !stick.down);
    std::cout<<"PASS radial deadzone / joystick drag / mouse priority / time-step / bounds\n";
}
