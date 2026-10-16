#pragma once
// Native DS graphic localization: rebuild SPR_CHR.PAK and SPR_CEL.PAK in RAM.
// Every source sprite entry is checksum-validated before writes, including
// relocated NCER tile pointers for the four Digivice selection states.
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstring>
#include <string>
#include <string_view>
#include <vector>
#include "dusk_graphics_runtime.hpp"

namespace dusk_sprites {
struct SpriteAsset {
    std::string_view locale;
    std::uint8_t pak_file_id; // exact Dusk USA FAT: 25 SPR_CEL, 26 SPR_CHR
    std::uint16_t sprite_id;
    std::uint32_t original_crc32;
    const std::uint8_t* compressed;
    std::uint32_t length;
};
#include "dusk_sprite_catalog.generated.hpp"

inline bool apply(std::vector<std::uint8_t>& rom,std::string_view locale,
                  std::string* reason=nullptr){
    auto fail=[&](const char* why)->bool{
        if(reason)*reason=why;
        return false;
    };
    if(rom.size()!=67108864u || std::memcmp(rom.data()+12,"A6RE",4)!=0)
        return fail("unexpected cartridge header");
    if(kSprites.empty())return true;
    const std::size_t fat=dusk_msgpak::read32(rom,0x48);
    const std::size_t fat_size=dusk_msgpak::read32(rom,0x4c);
    if(!fat || fat_size%8 || fat_size<27*8 ||
       std::uint64_t(fat)+fat_size>rom.size())
        return fail("invalid NitroFS index");

    constexpr std::size_t count=1627;
    constexpr std::size_t table_size=4+8*count;
    std::size_t tail=0;
    for(std::size_t i=0;i<fat_size/8;++i){
        const std::size_t lo=dusk_msgpak::read32(rom,fat+i*8);
        const std::size_t hi=dusk_msgpak::read32(rom,fat+i*8+4);
        if(hi<lo || hi>rom.size())return fail("untrusted FAT bounds");
        tail=std::max(tail,hi);
    }
    tail=(tail+511)&~std::size_t(511);

    struct Rebuild {
        std::uint8_t file_id;
        std::size_t destination;
        std::vector<std::uint8_t> bytes;
    };
    std::vector<Rebuild> staged;
    for(const std::uint8_t file_id:{std::uint8_t{25},std::uint8_t{26}}){
        std::array<const SpriteAsset*,count> entries{};
        std::size_t edits=0;
        for(const auto& spec:kSprites){
            if(spec.locale!=locale || spec.pak_file_id!=file_id)continue;
            if(spec.sprite_id>=count || !spec.compressed ||
               spec.length<4 || spec.length>0x400000 || spec.length%4 ||
               spec.compressed[0]!=0x30)
                return fail("malformed localized Nitro sprite");
            if(entries[spec.sprite_id])return fail("duplicate localized sprite ID");
            entries[spec.sprite_id]=&spec;
            ++edits;
        }
        if(!edits)continue;
        const std::size_t row=fat+file_id*8;
        const std::size_t src=dusk_msgpak::read32(rom,row);
        const std::size_t stop=dusk_msgpak::read32(rom,row+4);
        if(src>=stop || stop>rom.size() || stop-src<table_size ||
           dusk_msgpak::read32(rom,src)!=count)
            return fail("unsupported original Nitro sprite index");
        const std::size_t source_length=stop-src;
        std::vector<std::uint8_t> out(table_size);
        dusk_msgpak::write32(out,0,std::uint32_t(count));
        std::size_t previous=table_size;
        for(std::size_t i=0;i<count;++i){
            const std::size_t begin=dusk_msgpak::read32(rom,src+4+i*8);
            const std::uint32_t flagged=dusk_msgpak::read32(rom,src+8+i*8);
            const std::size_t len=flagged&0x7fffffffu;
            if(begin<previous || begin>source_length || len>source_length-begin)
                return fail("invalid source Nitro sprite record");
            previous=begin+len;
            const auto* spec=entries[i];
            if(spec && dusk_graphics::crc32(rom.data()+src+begin,len)
                        !=spec->original_crc32)
                return fail("original sprite content does not match locale manifest");
            const std::size_t newlen=spec?spec->length:len;
            if(out.size()+newlen+4>5*1024*1024)
                return fail("recompiled sprite pack exceeds safe bound");
            dusk_msgpak::write32(out,4+i*8,std::uint32_t(out.size()));
            dusk_msgpak::write32(out,8+i*8,
                         std::uint32_t(newlen)|(flagged&0x80000000u));
            if(spec)out.insert(out.end(),spec->compressed,spec->compressed+newlen);
            else out.insert(out.end(),
                    rom.begin()+src+begin,rom.begin()+src+begin+len);
            while(out.size()%4)out.push_back(0xff);
        }
        if(out.size()>rom.size()-tail)return fail("translated sprite packs will not fit");
        if(!std::all_of(rom.begin()+tail,rom.begin()+tail+out.size(),
                   [](std::uint8_t v){return v==0 || v==0xff;}))
            return fail("sprite pack destination is not free cartridge padding");
        staged.push_back({file_id,tail,std::move(out)});
        tail=(tail+staged.back().bytes.size()+511)&~std::size_t(511);
        if(tail>rom.size())return fail("translated sprite padding overflow");
    }
    // Atomic commit: no ROM writes until every source CRC and target is valid.
    for(const auto& item:staged){
        std::copy(item.bytes.begin(),item.bytes.end(),rom.begin()+item.destination);
        dusk_msgpak::write32(rom,fat+item.file_id*8,
                             std::uint32_t(item.destination));
        dusk_msgpak::write32(rom,fat+item.file_id*8+4,
                             std::uint32_t(item.destination+item.bytes.size()));
    }
    return true;
}
} // namespace dusk_sprites
