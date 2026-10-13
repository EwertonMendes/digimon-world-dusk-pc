#pragma once
#include "dusk/Layout.hpp"
#include <filesystem>
namespace dusk {
[[nodiscard]] LayoutSettings loadSettings(const std::filesystem::path& path);
[[nodiscard]] bool saveSettings(const std::filesystem::path& path, const LayoutSettings& settings);
}
