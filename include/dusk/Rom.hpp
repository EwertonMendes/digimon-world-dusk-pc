#pragma once
#include <cstdint>
#include <filesystem>
#include <optional>
#include <string>
#include <vector>

namespace dusk {
struct CodeSegment {
    std::uint32_t romOffset{};
    std::uint32_t entry{};
    std::uint32_t ramAddress{};
    std::uint32_t size{};
};
struct Overlay {
    std::uint32_t id{};
    std::uint32_t ramAddress{};
    std::uint32_t ramSize{};
    std::uint32_t bssSize{};
    std::uint32_t staticInitStart{};
    std::uint32_t staticInitEnd{};
    std::uint32_t fileId{};
    std::uint32_t reserved{};
    std::uint32_t fileStart{};
    std::uint32_t fileEnd{};
};
struct RomInfo {
    std::string title;
    std::string gameCode;
    std::string makerCode;
    std::uint64_t fileSize{};
    std::uint16_t headerCrc{};
    std::uint16_t computedHeaderCrc{};
    std::string sha256;
    CodeSegment arm9;
    CodeSegment arm7;
    std::uint32_t fntOffset{};
    std::uint32_t fntSize{};
    std::uint32_t fatOffset{};
    std::uint32_t fatSize{};
    std::uint32_t arm9OverlayOffset{};
    std::uint32_t arm9OverlaySize{};
    std::uint32_t arm7OverlayOffset{};
    std::uint32_t arm7OverlaySize{};
    std::uint32_t bannerOffset{};
    std::uint32_t fileCount{};
    std::vector<Overlay> arm9Overlays;
    std::vector<Overlay> arm7Overlays;
    std::vector<std::string> warnings;
    [[nodiscard]] bool matchesReferenceDusk() const;
    [[nodiscard]] bool headerCrcValid() const { return headerCrc == computedHeaderCrc; }
};
struct RomResult {
    std::optional<RomInfo> info;
    std::string error;
    [[nodiscard]] explicit operator bool() const { return info.has_value(); }
};
[[nodiscard]] RomResult inspectRom(const std::filesystem::path& path);
// Explicit opt-in for extraction. Outputs game-derived bytes: NEVER check into source control.
[[nodiscard]] bool extractCode(const std::filesystem::path& rom,
                               const std::filesystem::path& privateOutput,
                               std::string& error);
[[nodiscard]] std::string jsonReport(const RomInfo& info);
}
