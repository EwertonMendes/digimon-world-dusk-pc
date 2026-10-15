#include "dusk_arm9_runtime.hpp"
#include <fstream>
#include <iostream>
#include <iterator>
#include <vector>
#include <string>
int main(int argc,char** argv){
    if(argc!=2)return 2;
    std::ifstream f(argv[1],std::ios::binary);
    if(!f)return 3;
    std::vector<std::uint8_t> original((std::istreambuf_iterator<char>(f)),
                                       std::istreambuf_iterator<char>());
    if(original.size()!=67108864u)return 4;
    static_assert(dusk_arm9::kEntries.size()>=24);
    for(std::string_view lang:{"pt-BR","es-ES"}) {
        auto rom=original;
        std::string error;
        if(!dusk_arm9::apply(rom,lang,&error)){
            std::cerr<<lang<<": "<<error<<"\n";
            return 5;
        }
        size_t count=0;
        std::vector<bool> allowed(original.size(),false);
        for(const auto& row:dusk_arm9::kEntries){
            if(row.language!=lang)continue;
            std::vector<std::uint8_t> orig,translated;
            if(!dusk_msgpak::encode_text(row.original,orig)||
               !dusk_msgpak::encode_text(row.translated,translated))return 6;
            if(translated.size()>orig.size()||
               !std::equal(orig.begin(),orig.end(),original.begin()+row.offset)||
               !std::equal(translated.begin(),translated.end(),rom.begin()+row.offset))return 7;
            for(size_t i=row.offset;i<row.offset+translated.size();++i)allowed[i]=true;
            ++count;
        }
        if(count<12)return 8;
        for(size_t i=0;i<rom.size();++i)
            if(rom[i]!=original[i]&&!allowed[i])return 9;
        std::cout<<lang<<" verified "<<count<<" ARM9 UI text patches\n";
    }
    auto tampered=original;
    tampered[dusk_arm9::kEntries[0].offset]^=0x11;
    auto before=tampered;
    std::string reason;
    if(dusk_arm9::apply(tampered,dusk_arm9::kEntries[0].language,&reason))
        return 10;
    if(tampered!=before)return 11;
    return 0;
}
