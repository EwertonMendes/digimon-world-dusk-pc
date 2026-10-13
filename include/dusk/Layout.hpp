#pragma once
#include <algorithm>
namespace dusk {
constexpr int kScreenWidth = 256;
constexpr int kScreenHeight = 192;
enum class DisplayMode { modern, floating, classicHorizontal, classicVertical, primaryOnly };
struct Rect { int x{}, y{}, w{}, h{}; [[nodiscard]] bool contains(int px,int py) const { return px>=x && py>=y && px<x+w && py<y+h; } };
struct LayoutSettings {
    DisplayMode mode{DisplayMode::modern};
    float secondaryScale{0.55F};
    float secondaryOpacity{1.0F};
    float floatX{0.68F};
    float floatY{0.06F};
    bool showSecondary{true};
};
struct ScreenLayout { Rect primary; Rect secondary; bool visibleSecondary{}; };
[[nodiscard]] ScreenLayout computeLayout(int width, int height, const LayoutSettings& settings);
[[nodiscard]] bool screenToTouch(const ScreenLayout& layout, bool secondaryIsTouchscreen,
                                 int mouseX, int mouseY, int& touchX, int& touchY);
[[nodiscard]] const char* modeName(DisplayMode mode);
}
