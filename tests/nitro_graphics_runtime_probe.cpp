#include "dusk_graphics_runtime.hpp"
#include <fstream>
#include <iterator>
#include <vector>
#include <string>
#include <iostream>

int main(int argc,char** argv) {
    if(argc!=2)return 2;
    static constexpr std::uint8_t input[]={'1','2','3','4','5','6','7','8','9'};
    if(dusk_graphics::crc32(input,sizeof(input))!=0xcbf43926u)return 3;
    std::ifstream f(argv[1],std::ios::binary);
    if(!f)return 4;
    std::vector<std::uint8_t> rom((std::istreambuf_iterator<char>(f)),
                                   std::istreambuf_iterator<char>());
    if(rom.size()!=67108864u)return 5;
    auto before=rom;
    std::string error;
    for(auto lang:{"pt-BR","es-ES"}) {
        if(!dusk_graphics::apply(rom,lang,&error)) {
            std::cerr<<"Native resource verification: "<<error<<"\n";
            return 6;
        }
    }
    if(!dusk_graphics::kResources.empty()) {
        // When asset packs exist, test that original code segment and firmware
        // remain intact; only original matching FAT records and tail may change.
        const std::size_t arm9=dusk_msgpak::read32(before,0x20);
        const std::size_t arm9size=dusk_msgpak::read32(before,0x2c);
        if(!std::equal(before.begin()+arm9,before.begin()+arm9+arm9size,
                       rom.begin()+arm9))return 7;
    } else if(rom!=before)return 8;
    before[12]^=1;
    if(dusk_graphics::apply(before,"pt-BR"))return 9;
    std::cout<<"Native asset guard and original ROM data validated.\n";
    return 0;
}
