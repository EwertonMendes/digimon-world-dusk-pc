#include "dusk_sprite_runtime.hpp"
#include <algorithm>
#include <fstream>
#include <iterator>
#include <iostream>
#include <string>
#include <vector>
int main(int argc,char**argv){
    if(argc!=2)return 2;
    std::ifstream source(argv[1],std::ios::binary);
    if(!source)return 3;
    const std::vector<std::uint8_t> original(
        (std::istreambuf_iterator<char>(source)),
        std::istreambuf_iterator<char>());
    if(original.size()!=67108864)return 4;
    static_assert(dusk_sprites::kSprites.size()>=4,
                  "PT and ES must each ship localized native menu graphics");
    const std::size_t fat=dusk_msgpak::read32(original,0x48);
    const std::size_t old_start=dusk_msgpak::read32(original,fat+26*8);
    const std::size_t old_stop=dusk_msgpak::read32(original,fat+26*8+4);
    for(const std::string_view lang:{"pt-BR","es-ES"}){
        auto translated=original;
        std::string error;
        if(!dusk_sprites::apply(translated,lang,&error)){
            std::cerr<<lang<<": "<<error<<"\n";
            return 5;
        }
        const size_t a=dusk_msgpak::read32(translated,fat+26*8);
        const size_t z=dusk_msgpak::read32(translated,fat+26*8+4);
        if(a==old_start || a<=old_stop || z<=a || z>translated.size())return 6;
        if(!std::equal(original.begin()+old_start,original.begin()+old_stop,
                       translated.begin()+old_start))return 7;
        if(!std::equal(original.begin(),original.begin()+fat+26*8,
                       translated.begin()))return 8;
        for(const auto& record:dusk_sprites::kSprites){
            if(record.locale!=lang)continue;
            const size_t offset=dusk_msgpak::read32(translated,a+4+8*record.sprite_id);
            const size_t length=dusk_msgpak::read32(translated,a+8+8*record.sprite_id)&0x7fffffffu;
            if(length!=record.length || a+offset+length>z ||
               !std::equal(record.compressed,record.compressed+length,
                           translated.begin()+a+offset))return 9;
        }
        std::cout<<lang<<" replaced game-owned sprite records without changing original code/data\n";
    }
    auto corrupted=original;
    corrupted[old_start+4+8*388]^=0x7f;
    const auto before=corrupted;
    if(dusk_sprites::apply(corrupted,"pt-BR"))return 10;
    if(corrupted!=before)return 11;
    return 0;
}
