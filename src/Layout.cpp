#include "dusk/Layout.hpp"
#include <cmath>
namespace dusk {
namespace {
Rect fit(int x, int y, int width, int height) {
    if(width <= 0 || height <= 0) return {};
    const double scale = std::min(static_cast<double>(width)/kScreenWidth,
                                  static_cast<double>(height)/kScreenHeight);
    const int w = std::max(1, static_cast<int>(std::floor(kScreenWidth*scale)));
    const int h = std::max(1, static_cast<int>(std::floor(kScreenHeight*scale)));
    return {x+(width-w)/2, y+(height-h)/2, w, h};
}
}
ScreenLayout computeLayout(int width, int height, const LayoutSettings& s) {
    ScreenLayout out{};
    if(width <= 0 || height <= 0) return out;
    constexpr int margin = 16;
    const int x = std::min(margin, width/12);
    const int y = std::min(margin, height/12);
    const int aw = std::max(1, width-2*x);
    const int ah = std::max(1, height-2*y);
    out.visibleSecondary = s.showSecondary && s.mode != DisplayMode::primaryOnly;
    switch(s.mode) {
      case DisplayMode::modern: {
        const int column = std::clamp(aw/4, 1, 320);
        const int gap = std::min(16, aw/24);
        if (aw-column-gap < kScreenWidth/2) {
            out.primary = fit(x,y,aw,ah);
            out.secondary = fit(x+aw-column,y,column,ah/2);
        } else {
            out.primary = fit(x,y,aw-column-gap,ah);
            out.secondary = fit(x+aw-column,y,column,ah);
        }
        break;
      }
      case DisplayMode::floating: {
        out.primary = fit(x,y,aw,ah);
        const double scale = std::clamp(static_cast<double>(s.secondaryScale),0.25,1.0);
        const int sw = std::max(1,static_cast<int>(kScreenWidth*scale));
        const int sh = std::max(1,static_cast<int>(kScreenHeight*scale));
        const int fx = std::clamp(static_cast<int>(static_cast<double>(std::clamp(s.floatX,0.0F,1.0F))*std::max(0,width-sw)),0,std::max(0,width-sw));
        const int fy = std::clamp(static_cast<int>(static_cast<double>(std::clamp(s.floatY,0.0F,1.0F))*std::max(0,height-sh)),0,std::max(0,height-sh));
        out.secondary = {fx, fy, std::min(sw,width),std::min(sh,height)};
        break;
      }
      case DisplayMode::classicHorizontal: {
        const int gap = std::min(16,aw/20);
        const int half = std::max(1,(aw-gap)/2);
        out.primary = fit(x,y,half,ah);
        out.secondary = fit(x+half+gap,y,half,ah);
        break;
      }
      case DisplayMode::classicVertical: {
        const int gap = std::min(16,ah/20);
        const int half = std::max(1,(ah-gap)/2);
        out.secondary = fit(x,y,aw,half);
        out.primary = fit(x,y+half+gap,aw,half);
        break;
      }
      case DisplayMode::primaryOnly:
        out.primary = fit(x,y,aw,ah);
        break;
    }
    return out;
}
bool screenToTouch(const ScreenLayout& layout, bool secondaryIsTouchscreen,
                   int mx, int my, int& tx, int& ty) {
    const auto& r = secondaryIsTouchscreen ? layout.secondary : layout.primary;
    if(secondaryIsTouchscreen && !layout.visibleSecondary) return false;
    if(r.w<=0 || r.h<=0 || !r.contains(mx,my)) return false;
    tx = std::clamp((mx-r.x)*kScreenWidth/r.w,0,kScreenWidth-1);
    ty = std::clamp((my-r.y)*kScreenHeight/r.h,0,kScreenHeight-1);
    return true;
}
const char* modeName(DisplayMode m) {
    switch(m) {
        case DisplayMode::modern: return "Modern";
        case DisplayMode::floating: return "Floating";
        case DisplayMode::classicHorizontal: return "Classic horizontal";
        case DisplayMode::classicVertical: return "Classic vertical";
        case DisplayMode::primaryOnly: return "Primary only";
    }
    return "Unknown";
}
}
