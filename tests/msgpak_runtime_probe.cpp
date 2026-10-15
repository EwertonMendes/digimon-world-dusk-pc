#include "dusk_msgpak_runtime.hpp"
#include <fstream>
#include <iostream>
#include <iterator>
#include <vector>
#include <string>
int main(int argc,char** argv) {
    if(argc!=2)return 2;
    std::ifstream file(argv[1],std::ios::binary);
    if(!file)return 3;
    std::vector<uint8_t> original((std::istreambuf_iterator<char>(file)),
                                   std::istreambuf_iterator<char>());
    if(original.size()!=67108864u)return 4;
    const auto fst=dusk_msgpak::read32(original,0x48);
    if(fst+23*8+8>original.size())return 5;
    const auto old_begin=dusk_msgpak::read32(original,fst+23*8);
    const auto old_end=dusk_msgpak::read32(original,fst+23*8+4);
    for(const auto locale:{"pt-BR","es-ES"}) {
        auto image=original;std::string error;
        if(!dusk_msgpak::apply(image,locale,&error)) {
            std::cerr<<locale<<": "<<error<<"\n";return 6;
        }
        if(dusk_msgpak::read32(image,fst+23*8)==old_begin ||
           dusk_msgpak::read32(image,fst+23*8+4)<=old_end ||
           dusk_msgpak::read32(image,fst+23*8+4)>image.size())return 7;
        // Everything below the FAT MSG.PAK entry and the tail must remain
        // byte-identical: code banks, overlays and original message pack.
        for(size_t i=0;i<old_end;++i) {
            if(i>=fst+23*8 && i<fst+23*8+8)continue;
            if(image[i]!=original[i])return 8;
        }
        auto saved=dusk_msgpak::read32(image,fst+23*8);
        auto message_file=dusk_msgpak::read32(image,saved+4);
        auto msg_begin=saved+message_file;
        if(dusk_msgpak::read32(image,msg_begin)<8)return 9;
        std::cout<<locale<<" translated pack relocated to "<<saved
                 <<", first group at "<<msg_begin<<"\n";
    }
    // Unknown languages and untrusted images always fail closed.
    {
        auto copy=original;
        if(dusk_msgpak::apply(copy,"ja-JP"))return 10;
        if(copy!=original)return 11;
    }
    return 0;
}
