#pragma once
// Strict, all-or-nothing translated NitroFS resources. No screenshot overlays.
// Runs after validating the original embedded Dusk ROM, before native boot.
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstring>
#include <string>
#include <string_view>
#include <vector>
#include "dusk_msgpak_runtime.hpp"

namespace dusk_graphics {
struct ResourceEntry {
    std::string_view language;
    std::uint16_t file_id;
    std::uint32_t original_size;
    std::uint32_t original_crc32;
    const std::uint8_t* data;
    std::size_t replacement_size;
};
#include "dusk_graphics_catalog.generated.hpp"

inline std::uint32_t crc32(const std::uint8_t* source,std::size_t len) {
    std::uint32_t crc=0xffffffff;
    for(std::size_t i=0;i<len;++i) {
        crc^=source[i];
        for(int n=0;n<8;++n) crc=(crc>>1)^((crc&1)?0xedb88320u:0u);
    }
    return ~crc;
}

inline bool apply(std::vector<std::uint8_t>& rom,std::string_view language,
                  std::string* reason=nullptr) {
    const auto fail=[&](const char* why) {
        if(reason)*reason=why;
        return false;
    };
    if(rom.size()!=67108864u || std::memcmp(rom.data()+12,"A6RE",4)!=0)
        return fail("unexpected original ROM identity");
    const std::size_t fat=dusk_msgpak::read32(rom,0x48);
    const std::size_t fat_len=dusk_msgpak::read32(rom,0x4c);
    if(!fat || fat_len<8*24 || fat_len%8 || fat_len>1024*1024 ||
       fat+fat_len>rom.size())return fail("bad game file table");

    struct Patch {std::uint16_t id;std::size_t dst;const ResourceEntry* src;};
    std::vector<Patch> patches;
    std::size_t end=0;
    for(std::size_t i=0;i<fat_len/8;++i) {
        std::size_t a=dusk_msgpak::read32(rom,fat+i*8);
        std::size_t b=dusk_msgpak::read32(rom,fat+i*8+4);
        if(a>b || b>rom.size())return fail("invalid NitroFS entry");
        end=std::max(end,b);
    }
    end=(end+511)&~std::size_t(511);
    for(const auto& asset:kResources){
        if(asset.language!=language)continue;
        if(asset.file_id>=fat_len/8 || asset.file_id==23 ||
           !asset.data || !asset.replacement_size ||
           asset.replacement_size>16*1024*1024)
            return fail("invalid translated NitroFS asset");
        const std::size_t row=fat+asset.file_id*8;
        const std::size_t a=dusk_msgpak::read32(rom,row);
        const std::size_t b=dusk_msgpak::read32(rom,row+4);
        if(b-a!=asset.original_size ||
           crc32(rom.data()+a,b-a)!=asset.original_crc32)
            return fail("translated asset original checksum differs");
        if(!patches.empty() && std::any_of(patches.begin(),patches.end(),
                                           [&](const Patch& p){return p.id==asset.file_id;}))
            return fail("duplicate translated asset");
        if(end+asset.replacement_size>rom.size())return fail("translated assets do not fit ROM padding");
        if(!std::all_of(rom.begin()+end,rom.begin()+end+asset.replacement_size,
                        [](std::uint8_t value){return value==0 || value==0xff;}))
            return fail("tail contains non-padding data");
        patches.push_back({asset.file_id,end,&asset});
        end=(end+asset.replacement_size+511)&~std::size_t(511);
    }
    // Check all entries and destinations BEFORE applying any edits.
    for(const auto& patch:patches){
        const auto* source=patch.src;
        std::copy_n(source->data,source->replacement_size,rom.begin()+patch.dst);
        dusk_msgpak::write32(rom,fat+8*patch.id,std::uint32_t(patch.dst));
        dusk_msgpak::write32(rom,fat+8*patch.id+4,
                             std::uint32_t(patch.dst+source->replacement_size));
    }
    return true;
}
} // namespace dusk_graphics
