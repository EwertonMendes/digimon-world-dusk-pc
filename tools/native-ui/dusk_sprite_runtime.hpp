#pragma once
// Replace original game-owned sprite data in memory, never overlay English UI.
// Each SPR_CHR.PAK member is a Dusk RLE encoded NCGR sprite with an independent
// ID. The pack table is rebuilt so translated art may use more bytes.
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
    std::uint16_t sprite_id;
    std::uint32_t original_crc32;
    const std::uint8_t* compressed;
    std::uint32_t length;
};
#include "dusk_sprite_catalog.generated.hpp"

inline bool apply(std::vector<std::uint8_t>& rom,std::string_view locale,
                  std::string* reason=nullptr){
    auto fail=[&](const char* why)->bool{if(reason)*reason=why;return false;};
    if(rom.size()!=67108864u || std::memcmp(rom.data()+12,"A6RE",4)!=0)
        return fail("unexpected cartridge header");
    if(kSprites.empty())return true;
    const std::uint32_t fat=dusk_msgpak::read32(rom,0x48);
    const std::uint32_t fat_size=dusk_msgpak::read32(rom,0x4c);
    if(!fat || fat_size%8 || fat_size<27*8 || std::uint64_t(fat)+fat_size>rom.size())
        return fail("invalid NitroFS index");
    const std::size_t entry=fat+26*8; // Verified Dusk USA dat/SPR_CHR.PAK
    const std::size_t source=dusk_msgpak::read32(rom,entry);
    const std::size_t source_end=dusk_msgpak::read32(rom,entry+4);
    if(source>=source_end || source_end>rom.size())
        return fail("sprite FAT record invalid");
    const std::size_t old_size=source_end-source;
    if(old_size<13020 || dusk_msgpak::read32(rom,source)!=1627u)
        return fail("unsupported sprite index format");
    constexpr size_t count=1627;
    constexpr size_t header=4+8*count;
    if(header!=13020 || source+header>source_end)
        return fail("invalid sprite table length");

    std::vector<const SpriteAsset*> replacement(count,nullptr);
    size_t modifications=0;
    for(const auto& patch:kSprites) {
        if(patch.locale!=locale)continue;
        if(patch.sprite_id>=count || !patch.compressed || !patch.length ||
           patch.length>0x400000 || (patch.length&3))
            return fail("invalid replacement sprite");
        if(replacement[patch.sprite_id])
            return fail("duplicate translated sprite");
        if(patch.compressed[0]!=0x30)
            return fail("expected Nintendo RLE-compressed sprite data");
        replacement[patch.sprite_id]=&patch;
        ++modifications;
    }
    if(!modifications)return true;
    std::vector<std::uint8_t> payload(header);
    dusk_msgpak::write32(payload,0,std::uint32_t(count));
    size_t prev_end=header;
    for(size_t i=0;i<count;++i) {
        const size_t begin=dusk_msgpak::read32(rom,source+4+i*8);
        const std::uint32_t lengthflag=dusk_msgpak::read32(rom,source+8+i*8);
        const size_t length=lengthflag&0x7fffffffu;
        if(begin<prev_end || begin>old_size || length>old_size-begin)
            return fail("invalid original sprite table bounds");
        prev_end=begin+length;
        const auto* patch=replacement[i];
        if(patch && dusk_graphics::crc32(rom.data()+source+begin,length)
                        !=patch->original_crc32)
            return fail("sprite source checksum does not match");
        const size_t newlen=patch?patch->length:length;
        if(payload.size()>4*1024*1024-newlen)
            return fail("translated sprite pack is too large");
        dusk_msgpak::write32(payload,4+i*8,std::uint32_t(payload.size()));
        dusk_msgpak::write32(payload,8+i*8,
                            std::uint32_t(newlen)|(lengthflag&0x80000000u));
        if(patch)payload.insert(payload.end(),patch->compressed,patch->compressed+newlen);
        else payload.insert(payload.end(),
                            rom.begin()+source+begin,rom.begin()+source+begin+length);
        while(payload.size()%4)payload.push_back(0xff);
    }
    size_t tail=0;
    for(size_t i=0;i<fat_size/8;++i){
        const auto a=dusk_msgpak::read32(rom,fat+i*8);
        const auto z=dusk_msgpak::read32(rom,fat+i*8+4);
        if(z<a || z>rom.size())return fail("invalid ROM FAT bounds");
        tail=std::max(tail,size_t(z));
    }
    tail=(tail+511)&~size_t(511);
    if(tail+payload.size()>rom.size())return fail("sprite pack cannot fit ROM padding");
    if(!std::all_of(rom.begin()+tail,rom.begin()+tail+payload.size(),
                    [](std::uint8_t c){return c==0 || c==0xff;}))
        return fail("sprite destination is not empty padding");
    std::copy(payload.begin(),payload.end(),rom.begin()+tail);
    dusk_msgpak::write32(rom,entry,std::uint32_t(tail));
    dusk_msgpak::write32(rom,entry+4,std::uint32_t(tail+payload.size()));
    return true;
}
} // namespace dusk_sprites
