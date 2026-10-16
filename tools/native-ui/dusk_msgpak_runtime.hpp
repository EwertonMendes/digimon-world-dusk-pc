#pragma once
// Host-side resource rebuilder for the verified Digimon World Dusk USA cartridge.
// Applied IN MEMORY after original ROM identity validation and before DS boot.
// This does not modify ARM instructions, AOT banks, save data or the installed ROM.
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstring>
#include <string>
#include <string_view>
#include <vector>

namespace dusk_msgpak {
inline uint32_t read32(const std::vector<uint8_t>& d,size_t i) {
    if(i+4>d.size())return 0xffffffffu;
    return uint32_t(d[i])|(uint32_t(d[i+1])<<8)|(uint32_t(d[i+2])<<16)|(uint32_t(d[i+3])<<24);
}
inline uint16_t read16(const std::vector<uint8_t>& d,size_t i) {
    if(i+2>d.size())return 0xffff;
    return uint16_t(d[i])|uint16_t(d[i+1]<<8);
}
inline void write32(std::vector<uint8_t>& d,size_t i,uint32_t v) {
    if(i+4>d.size())return;
    for(int n=0;n<4;++n)d[i+n]=uint8_t(v>>(n*8));
}
inline void push16(std::vector<uint8_t>& d,uint16_t v) {
    d.push_back(uint8_t(v));d.push_back(uint8_t(v>>8));
}
inline void push32(std::vector<uint8_t>& d,uint32_t v) {
    for(int n=0;n<4;++n)d.push_back(uint8_t(v>>(8*n)));
}
inline uint16_t encode_char(char32_t c) {
    if(c==' ')return 0;
    if(c>='0'&&c<='9')return uint16_t(c-'0'+1);
    if(c>='A'&&c<='Z')return uint16_t(c-'A'+0x20);
    if(c>='a'&&c<='z')return uint16_t(c-'a'+0x3a);
    switch(c) {
        case U'/':return 0x0b;case U'%':return 0x0c;case U':':return 0x0d;
        case U'\'':return 0x0e;case U'"':return 0x0f;case U',':return 0x11;
        case U'.':return 0x12;case U'!':return 0x13;case U'?':return 0x14;
        case U'¿':return 0x9f;case U'¡':return 0x9e;
        case U'(':return 0x15;case U')':return 0x16;case U'+':return 0x17;
        case U'-':return 0x18;case U'=':return 0x19;
        case U'à':return 0xa0;case U'á':return 0xa1;case U'â':return 0xa2;
        case U'ã':return 0xa3;case U'ä':return 0xa4;case U'ç':return 0xa7;
        case U'è':return 0xa8;case U'é':return 0xa9;case U'ê':return 0xaa;
        case U'ì':return 0xac;case U'í':return 0xad;case U'î':return 0xae;
        case U'ñ':return 0xb1;case U'ò':return 0xb2;case U'ó':return 0xb3;
        case U'ô':return 0xb4;case U'õ':return 0xb5;case U'ú':return 0xb9;
        case U'ü':return 0xbb;case U'À':return 0x80;case U'Á':return 0x81;
        case U'Â':return 0x82;case U'Ã':return 0x83;case U'Ç':return 0x87;
        case U'É':return 0x89;case U'Í':return 0x8d;case U'Ñ':return 0x91;
        case U'Ó':return 0x93;case U'Ô':return 0x94;case U'Õ':return 0x95;
        case U'Ú':return 0x99;
        default:return 0xffff;
    }
}
inline bool encode_text(std::u32string_view text,std::vector<uint8_t>& out) {
    out.clear();
    for(size_t i=0;i<text.size();) {
        if(text.substr(i,13)==U"[PLAYER_NAME]"){push16(out,0xffed);i+=13;continue;}
        if(text.substr(i,5)==U"[END]"){push16(out,0xfffe);i+=5;continue;}
        if(text.substr(i,5)==U"[RED]"){push16(out,0xffee);i+=5;continue;}
        if(text.substr(i,7)==U"[GREEN]"){push16(out,0xffea);i+=7;continue;}
        if(text[i]==U'\n'){push16(out,0xfffd);++i;continue;}
        const auto code=encode_char(text[i++]);
        if(code==0xffff)return false;
        push16(out,code);
    }
    push16(out,0xffff);
    return true;
}
struct Replacement {
    int group;
    int id;
    std::string_view language;
    std::u32string_view translated;
};
// This header is generated deterministically from translations/msgpak/*.json.
#include "dusk_msgpak_catalog.generated.hpp"

inline bool rebuild_group(const std::vector<uint8_t>& original,int group,
                          std::string_view language,std::vector<uint8_t>& output,
                          int& replacements) {
    if(original.size()<8)return false;
    const uint32_t table_size=read32(original,0);
    if(table_size<4 || table_size%4 || table_size>original.size())return false;
    const size_t count=table_size/4;
    if(count>4096)return false;
    std::vector<uint32_t> offsets(count+1);
    for(size_t i=0;i<count;++i) {
        offsets[i]=read32(original,i*4);
        if(offsets[i]<table_size || offsets[i]>=original.size() || offsets[i]%2)return false;
        if(i && offsets[i]<=offsets[i-1])return false;
    }
    offsets[count]=uint32_t(original.size());
    if(offsets[count]%2)return false;
    output.assign(table_size,0);
    for(size_t i=0;i<count;++i) {
        write32(output,i*4,uint32_t(output.size()));
        bool changed=false;
        for(const auto& row:proof) {
            if(row.group!=group || row.id!=int(i) || row.language!=language)continue;
            const auto translated=row.translated;
            std::vector<uint8_t> encoded;
            // Preserve original end marker type; never inject an extra game event.
            if(!encode_text(translated,encoded))return false;
            auto begin=original.begin()+offsets[i],end=original.begin()+offsets[i+1];
            bool has_end=false;
            for(auto it=begin;it+1<end;it+=2) {
                if(uint8_t(*it)==0xfe && uint8_t(*(it+1))==0xff)has_end=true;
            }
            bool new_end=false;
            for(size_t j=0;j+1<encoded.size();j+=2)
                if(encoded[j]==0xfe && encoded[j+1]==0xff)new_end=true;
            if(has_end!=new_end)return false;
            // Never remove game variables, color toggles, or other control
            // markers. Only textual glyph codes and line breaks may change.
            auto controls=[](const std::vector<uint8_t>& data,size_t begin,size_t end){
                std::vector<uint16_t> result;
                for(size_t i=begin;i+1<end;i+=2) {
                    const auto value=read16(data,i);
                    if(value>=0xffe7 && value<=0xfff0)result.push_back(value);
                }
                return result;
            };
            if(controls(original,offsets[i],offsets[i+1]) !=
               controls(encoded,0,encoded.size()))return false;
            const uint16_t original_last=read16(original,offsets[i+1]-2);
            if(original_last==0xfffe) {
                // Dialogue entries end directly with [END] (FE FF).
                // Do not append another FFFF terminator: the game's paging
                // engine treats that as another record, not spare padding.
                if(encoded.size()<4 || read16(encoded,encoded.size()-4)!=0xfffe)
                    return false;
                encoded.resize(encoded.size()-2);
            } else if(original_last!=0xffff) return false;
            output.insert(output.end(),encoded.begin(),encoded.end());
            changed=true;++replacements;break;
        }
        if(!changed)output.insert(output.end(),original.begin()+offsets[i],original.begin()+offsets[i+1]);
        if(output.size()>4*1024*1024)return false;
    }
    return true;
}
// Caller must have verified exact Dusk USA SHA-1 before invoking this function.
inline bool apply(std::vector<uint8_t>& rom,std::string_view language,std::string* error=nullptr) {
    const auto fail=[&](const char* why)->bool{if(error)*error=why;return false;};
    if(std::find(kPackLanguages.begin(),kPackLanguages.end(),language)==kPackLanguages.end())
        return fail("no gameplay catalog for selected language");
    if(rom.size()!=67108864u || std::memcmp(rom.data()+12,"A6RE",4)!=0)
        return fail("unexpected cartridge identity");
    const uint32_t fat=read32(rom,0x48),fat_size=read32(rom,0x4c);
    if(fat_size%8 || fat_size<24*8 || fat_size>1024*1024 || uint64_t(fat)+fat_size>rom.size())
        return fail("invalid cartridge file table");
    const size_t f23=fat+23*8;
    const uint32_t pak_begin=read32(rom,f23),pak_end=read32(rom,f23+4);
    if(pak_begin!=18342912u || pak_end-pak_begin!=1617556u)
        return fail("MSG.PAK resource identity differs from verified USA");
    std::vector<uint8_t> original(rom.begin()+pak_begin,rom.begin()+pak_end);
    constexpr size_t groups=138;
    if(read32(original,0)!=groups || read32(original,4)!=4+8*groups)
        return fail("unexpected MSG.PAK table");
    std::vector<uint8_t> output(4+groups*8,0);
    write32(output,0,uint32_t(groups));
    int replaced=0;
    for(size_t group=0;group<groups;++group) {
        const uint32_t off=read32(original,4+group*8),szflag=read32(original,8+group*8);
        const uint32_t size=szflag&0x7fffffffu;
        if(!(szflag&0x80000000u) || off<4+groups*8 ||
           size==0 || uint64_t(off)+size>original.size())
            return fail("invalid MSG.PAK subfile");
        std::vector<uint8_t> sub(original.begin()+off,original.begin()+off+size);
        std::vector<uint8_t> translated;
        if(std::any_of(proof.begin(),proof.end(),[&](const Replacement& r){
            return r.group==int(group) && r.language==language;
        })) {
            if(!rebuild_group(sub,int(group),language,translated,replaced))
                return fail("invalid internal message offsets or terminators");
        } else translated=std::move(sub);
        if(output.size()+translated.size()>=0x7fffffff)
            return fail("translated messages exceed supported pack size");
        write32(output,4+group*8,uint32_t(output.size()));
        write32(output,8+group*8,uint32_t(translated.size())|0x80000000u);
        output.insert(output.end(),translated.begin(),translated.end());
    }
    const int expected=int(std::count_if(proof.begin(),proof.end(),
        [&](const Replacement& r){return r.language==language;}));
    if(replaced!=expected)return fail("gameplay message IDs did not match");
    uint32_t highest=0;
    for(uint32_t i=0;i<fat_size/8;++i) {
        const uint32_t lo=read32(rom,fat+8*i),hi=read32(rom,fat+8*i+4);
        if(lo>hi || hi>rom.size())return fail("invalid game file bounds");
        highest=std::max(highest,hi);
    }
    const uint64_t dest=(uint64_t(highest)+511u)&~uint64_t(511u);
    if(dest+output.size()>rom.size())return fail("not enough verified cartridge padding");
    if(!std::all_of(rom.begin()+dest,rom.begin()+dest+output.size(),
                    [](uint8_t x){return x==0xff || x==0; }))
        return fail("cartridge tail is not empty padding");
    std::copy(output.begin(),output.end(),rom.begin()+dest);
    write32(rom,f23,uint32_t(dest));
    write32(rom,f23+4,uint32_t(dest+output.size()));
    return true;
}
} // namespace dusk_msgpak
