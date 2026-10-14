// The SDL3 overlay owns the left analog stick while PC Options is visible.
// The DS scheduler, framebuffer and audio still run, but guest keys are gated.
#include "dusk_native_ui.h"
#include <cassert>
#include <cmath>
#include <iostream>
#include <limits>

int main() {
    using dusk_native::MenuDirection;
    dusk_native::MenuStickNavigation nav;
    assert(nav.poll(0.f,0.f)==MenuDirection::None);
    assert(nav.poll(0.49f,0.f)==MenuDirection::None);
    assert(nav.poll(0.9f,0.1f)==MenuDirection::Right);
    for(int i=0;i<17;++i)assert(nav.poll(0.9f,0.1f)==MenuDirection::None);
    assert(nav.poll(0.9f,0.1f)==MenuDirection::Right); // initial repeat
    for(int i=0;i<4;++i)assert(nav.poll(0.9f,0.1f)==MenuDirection::None);
    assert(nav.poll(0.9f,0.1f)==MenuDirection::Right); // fast repeat
    assert(nav.poll(0.f,-.8f)==MenuDirection::Up);     // immediate direction change
    assert(nav.poll(.1f,-.5f)==MenuDirection::None);  // hysteresis
    assert(nav.poll(0.f,0.f)==MenuDirection::None);    // no sticky nav
    assert(nav.poll(0.f,-.8f)==MenuDirection::Up);
    nav.reset();
    assert(nav.poll(0.f,0.f)==MenuDirection::None);
    assert(nav.poll(-.9f,0.f)==MenuDirection::Left);
    assert(nav.poll(0.f,.9f)==MenuDirection::Down);
    assert(nav.poll(std::numeric_limits<float>::quiet_NaN(),0.f)==MenuDirection::None);
    assert(nav.held==MenuDirection::None);

    // A held gamepad cannot cause an endless scroll after stick release.
    for(int i=0;i<360;++i) {
        const auto d=nav.poll(0.f,0.f);
        assert(d==MenuDirection::None);
    }
    // Navigation can resume immediately after the modal/overlay reopens.
    nav.reset();
    assert(nav.poll(-.9f,-.2f)==MenuDirection::Left);
    assert(nav.poll(.2f,.8f)==MenuDirection::Down);
    std::cout << "PASS PC Options left stick deadzone/repeat/cancel/nav\n";
}
