// ROM-free regression for optional presentation cadence.
// One out of each two completed guest frames is rendered at native DS cadence.
// This MUST NOT be used to skip guest scheduler, input, audio, GPU or digests.
#include "dusk_native_ui.h"
#include <cassert>
#include <cstdint>
#include <iostream>
int main() {
    using namespace dusk_native;
    Config c{};
    // Immersive PC defaults to full visual rate; the 30fps option is opt-in.\n    assert(!c.half_present);
    std::uint64_t rendered_30=0, rendered_60=0;
    constexpr std::uint64_t virtual_guest_frames=1200;
    for(std::uint64_t n=0;n<virtual_guest_frames;++n) {
        rendered_30 += should_present(n,true);
        rendered_60 += should_present(n,false);
        assert(should_present(n,true)==((n%2u)==0u));
    }
    assert(rendered_30==600 && rendered_60==1200);
    assert(should_present(100,true));
    assert(!should_present(101,true));
    assert(should_present(101,false));
    // Rendering 600 guest snapshots is ~29.913 Hz at original 59.826 Hz,
    // NOT an exact 30.000Hz display rate and NOT half-speed game logic.
    std::cout<<"PASS 1200 guest updates, 600 or 1200 visual presents\n";
}