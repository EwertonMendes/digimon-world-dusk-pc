#include <cstdint>
#include <string>
struct SDL_Renderer {}; struct SDL_Texture {};
struct SDL_FRect {float x,y,w,h;}; struct SDL_Rect{int x,y,w,h;};struct SDL_FColor{float r,g,b,a;};
struct SDL_FPoint{float x,y;}; struct SDL_Vertex{ SDL_FPoint position;SDL_FColor color; SDL_FPoint tex_coord;};
constexpr int SDL_BLENDMODE_BLEND=1,SDL_PIXELFORMAT_RGBA32=2,SDL_TEXTUREACCESS_STATIC=3,SDL_SCALEMODE_LINEAR=4;
inline void SDL_SetRenderDrawBlendMode(SDL_Renderer*,int){}; inline void SDL_SetRenderDrawColor(SDL_Renderer*,int,int,int,int){};
inline void SDL_RenderFillRect(SDL_Renderer*, SDL_FRect*){};
inline void SDL_RenderGeometry(SDL_Renderer*,SDL_Texture*,SDL_Vertex*,int,int*,int){};
inline SDL_Texture* SDL_CreateTexture(SDL_Renderer*,int,int,int,int){static SDL_Texture t;return &t;}
inline bool SDL_UpdateTexture(SDL_Texture*,void*,const void*,int){return true;}
inline void SDL_DestroyTexture(SDL_Texture*){};
inline bool SDL_SetTextureBlendMode(SDL_Texture*,int){return true;};inline bool SDL_SetTextureScaleMode(SDL_Texture*,int){return true;};
inline bool SDL_SetTextureColorMod(SDL_Texture*,uint8_t,uint8_t,uint8_t){return true;};inline bool SDL_SetTextureAlphaMod(SDL_Texture*,uint8_t){return true;};
inline void SDL_RenderTexture(SDL_Renderer*,SDL_Texture*,SDL_FRect*,SDL_FRect*){};
inline void SDL_SetRenderClipRect(SDL_Renderer*,const SDL_Rect*){};
namespace dusk_native {struct Rect{int x,y,w,h;};struct Geometry{Rect play, pip_bar,pip_restore,pip_swap,pip_minimize,settings;};enum class Layout{Focus=5};}
struct FrontendPresentation{struct {struct {dusk_native::Layout layout=dusk_native::Layout::Focus;bool focus_top=false;} cfg;bool menu_open=false;} dusk;};
const char* dusk_label(int){return "Screen layout";}std::string dusk_value(const FrontendPresentation&,int){return "25%";}
namespace dusk_modern {
using Rect=dusk_native::Rect;
struct Item{Rect rect;int kind,value;};
struct View{Rect panel, title,tabs[4],content,close,footer;Item items[16];int count=0;int content_height=0;};
struct State {int focus=0,tab=0,scroll=0;};inline State state{};
View calculate(const dusk_native::Geometry&,const FrontendPresentation&){return {};}
int max_scroll(const View&){return 0;}
}
#include "dusk_material_renderer.hpp"
int main(){SDL_Renderer r;dusk_native::Geometry g{};g.play={0,0,1280,720};FrontendPresentation p;if(!dusk_font::ensure(&r)) return 4;if(dusk_font::measure("Settings",24,true)<30) return 5;dusk_material::panel(&r,p,g);return 0;}