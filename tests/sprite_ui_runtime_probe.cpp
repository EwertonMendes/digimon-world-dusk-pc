#include "dusk_sprite_runtime.hpp"
#include <algorithm>
#include <fstream>
#include <iterator>
#include <iostream>
#include <string>
#include <vector>

int main(int argc,char**argv) {
    if(argc!=2)return 2;
    std::ifstream file(argv[1],std::ios::binary);
    if(!file)return 3;
    const std::vector<std::uint8_t> original(
        (std::istreambuf_iterator<char>(file)),std::istreambuf_iterator<char>());
    if(original.size()!=67108864u)return 4;
    static_assert(dusk_sprites::kSprites.size()>=20,
                  "both locales must include original UI labels and isolated NCER state assets");
    const auto fat=dusk_msgpak::read32(original,0x48);
    const auto arm9=dusk_msgpak::read32(original,0x20);
    const auto arm9_size=dusk_msgpak::read32(original,0x2c);
    for(const std::string_view locale:{"pt-BR","es-ES"}){
        auto modified=original;
        std::string error;
        if(!dusk_sprites::apply(modified,locale,&error)){
            std::cerr<<locale<<": "<<error<<"\n";
            return 5;
        }
        for(const std::size_t fileid:{25u,26u}){
            const auto old_start=dusk_msgpak::read32(original,fat+fileid*8);
            const auto old_stop=dusk_msgpak::read32(original,fat+fileid*8+4);
            const auto now_start=dusk_msgpak::read32(modified,fat+fileid*8);
            const auto now_stop=dusk_msgpak::read32(modified,fat+fileid*8+4);
            if(now_start==old_start||now_start<=old_stop||
               now_stop<=now_start||now_stop>modified.size())return 6;
            if(!std::equal(original.begin()+old_start,original.begin()+old_stop,
                           modified.begin()+old_start))return 7;
            if(dusk_msgpak::read32(modified,now_start)!=1627u)return 8;
        }
        if(!std::equal(original.begin()+arm9,
                       original.begin()+arm9+arm9_size,
                       modified.begin()+arm9))return 9;
        for(const auto& record:dusk_sprites::kSprites){
            if(record.locale!=locale)continue;
            const std::size_t start=dusk_msgpak::read32(
                modified,fat+record.pak_file_id*8);
            const std::size_t stop=dusk_msgpak::read32(
                modified,fat+record.pak_file_id*8+4);
            const std::size_t a=dusk_msgpak::read32(
                modified,start+4+8*record.sprite_id);
            const std::size_t n=dusk_msgpak::read32(
                modified,start+8+8*record.sprite_id)&0x7fffffffu;
            if(n!=record.length || start+a+n>stop ||
               !std::equal(record.compressed,record.compressed+n,
                           modified.begin()+start+a))return 10;
        }
        std::cout<<locale<<": translated original NCGR+NCER packages verified in RAM\n";
    }
    auto corrupted=original;
    const std::size_t original_chr=dusk_msgpak::read32(original,fat+26*8);
    const auto rec=dusk_msgpak::read32(original,original_chr+4+8*479);
    corrupted[original_chr+rec+8]^=0x1;
    const auto before=corrupted;
    if(dusk_sprites::apply(corrupted,"pt-BR"))return 11;
    if(corrupted!=before)return 12;
    return 0;
}
