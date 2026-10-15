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
    static_assert(dusk_msgpak::proof.size()>=36, "must include repeatable gameplay checks in two locales");
    auto record=[](const std::vector<uint8_t>& data,int group,int id) {
        using dusk_msgpak::read32;
        const size_t fat=read32(data,0x48);
        const size_t pak=read32(data,fat+23*8);
        const size_t sub=pak+read32(data,pak+4+group*8);
        const auto bytes=read32(data,sub);
        if(bytes%4 || id<0 || (size_t)id>=bytes/4)
            return std::vector<uint8_t>{};
        const size_t lo=read32(data,sub+id*4);
        const size_t hi=(size_t)(id+1)<bytes/4 ? read32(data,sub+(id+1)*4)
                           : (read32(data,pak+8+group*8)&0x7fffffffu);
        if(hi<=lo || sub+hi>data.size())return std::vector<uint8_t>{};
        return std::vector<uint8_t>(data.begin()+sub+lo,data.begin()+sub+hi);
    };
    const auto original_menu=record(original,124,45);
    if(original_menu.empty())return 12;
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
        // Every translated row must be present in the relocated file, using
        // the exact DS two-byte encoding and terminator, not a fake SDL label.
        for(const auto& row:dusk_msgpak::proof) {
            if(row.language!=locale)continue;
            std::vector<uint8_t> expected;
            if(!dusk_msgpak::encode_text(row.translated,expected))return 13;
            const auto before=record(original,row.group,row.id);
            const auto after=record(image,row.group,row.id);
            if(before.empty() || after.empty() || before==after)return 14;
            if(dusk_msgpak::read16(before,before.size()-2)==0xfffe)
                expected.resize(expected.size()-2);
            if(after!=expected) {
                std::cerr<<"bad replacement "<<locale<<" "<<row.group<<"/"<<row.id<<"\\n";
                return 15;
            }
        }
        if(record(image,124,45)==original_menu)return 16;
        if(record(image,2,0)!=record(original,2,0))return 17;
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
