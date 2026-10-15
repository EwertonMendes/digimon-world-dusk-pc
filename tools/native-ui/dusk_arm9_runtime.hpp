#pragma once
// Data-only text translations at verified ROM offsets inside Dusk USA ARM9.
// The guest data is replaced AFTER the original full-ROM SHA identity gate
// and BEFORE the ROM's ARM9 image is copied into emulated RAM.
// Never modifies instructions, tables, length-changing pointers or EEPROM.
#include <algorithm>
#include <array>
#include <cstdint>
#include <string>
#include <string_view>
#include <vector>
#include "dusk_msgpak_runtime.hpp"

namespace dusk_arm9 {
struct Arm9Entry {
    std::uint32_t offset;
    std::string_view language;
    std::u32string_view original;
    std::u32string_view translated;
};
#include "dusk_arm9_catalog.generated.hpp"

inline bool apply(std::vector<std::uint8_t>& rom,std::string_view language,std::string* reason=nullptr) {
    auto fail=[&](const char* message)->bool{
        if(reason)*reason=message;
        return false;
    };
    if(std::find(kLanguages.begin(),kLanguages.end(),language)==kLanguages.end())
        return fail("ARM9 UI pack not installed");
    if(rom.size()!=67108864u || std::memcmp(rom.data()+12,"A6RE",4)!=0)
        return fail("unexpected cartridge header");
    const std::uint32_t arm9_begin=dusk_msgpak::read32(rom,0x20);
    const std::uint32_t arm9_length=dusk_msgpak::read32(rom,0x2c);
    if(arm9_begin!=16384u || arm9_length!=1249432u ||
       std::uint64_t(arm9_begin)+arm9_length>rom.size())
        return fail("unexpected ARM9 file identity");
    struct Patch {size_t offset;std::vector<std::uint8_t> data;size_t original_size;};
    std::vector<Patch> changes;
    size_t previous_end=0;
    // Gather and validate all rows before committing any modification.
    // Thus a bad locale entry cannot partly corrupt text state.
    for(const auto& row:kEntries){
        if(row.language!=language)continue;
        const size_t pos=row.offset;
        std::vector<std::uint8_t> expected,translated;
        if(!dusk_msgpak::encode_text(row.original,expected) ||
           !dusk_msgpak::encode_text(row.translated,translated))
            return fail("unencodable ARM9 locale row");
        if(translated.size()>expected.size() || pos<arm9_begin ||
           pos+expected.size()>size_t(arm9_begin)+arm9_length ||
           pos<previous_end)
            return fail("ARM9 text would overlap a neighbor");
        if(!std::equal(expected.begin(),expected.end(),rom.begin()+pos)) {
            if(reason)*reason="ARM9 source mismatch at "+std::to_string(row.offset);
            return false;
        }
        changes.push_back({pos,std::move(translated),expected.size()});
        previous_end=pos+expected.size();
    }
    if(changes.empty())return fail("no ARM9 entries for requested language");
    for(const auto& patch:changes)
        std::copy(patch.data.begin(),patch.data.end(),rom.begin()+patch.offset);
    return true;
}
} // namespace dusk_arm9
