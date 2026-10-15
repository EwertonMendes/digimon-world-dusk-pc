#pragma once
// GPU text from pre-rasterized Inter Display glyph coverage (OFL).
// Independent of OS fonts, SDL_ttf, window DPI and the original NDS pixel art.
#include "dusk_font_atlas.hpp"
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <string>
#include <vector>

namespace dusk_font {
struct Color { uint8_t r,g,b,a=255; };
inline Color white{242,239,255,255};
struct Cache { SDL_Renderer* renderer=nullptr; SDL_Texture* texture=nullptr; };
inline Cache cache{};
inline SDL_Texture* ensure(SDL_Renderer* renderer) {
    if (cache.renderer == renderer && cache.texture) return cache.texture;
    if (cache.renderer != renderer) { cache.renderer=renderer; cache.texture=nullptr; }
    const auto data=dusk_font_assets::kDataBase64;
    std::vector<uint8_t> compressed;
    compressed.reserve(100000);
    uint32_t bits=0;int used=0;
    for (const char *p=data;*p;p++) {
        unsigned char c=*p;
        int v=(c>='A'&&c<='Z')?c-'A':(c>='a'&&c<='z')?c-'a'+26:
              (c>='0'&&c<='9')?c-'0'+52:c=='+'?62:c=='/'?63:-1;
        if(v<0)continue;
        bits=(bits<<6)|uint32_t(v);used+=6;
        if(used>=8) {used-=8;compressed.push_back(uint8_t(bits>>used));bits&=(1u<<used)-1u;}
    }
    const int w=dusk_font_assets::kWidth,h=dusk_font_assets::kHeight;
    std::vector<uint32_t> rgba(size_t(w)*size_t(h), 0);
    // RGBA32 has the expected byte layout on Windows, macOS, Linux and Android.
    auto *bytes=reinterpret_cast<uint8_t*>(rgba.data());
    size_t at=0,pos=0;
    while(pos<compressed.size() && at<rgba.size()) {
        uint8_t code=compressed[pos++];
        size_t len=(code&127)+1;
        if(code&128) {at=std::min(rgba.size(),at+len);continue;}
        for(size_t i=0;i<len && at<rgba.size();i++) {
            if(pos+i/2>=compressed.size())return nullptr;
            uint8_t pair=compressed[pos+i/2];
            uint8_t alpha=((i&1)?(pair&15):(pair>>4))*17;
            size_t idx=(at++)*4;
            bytes[idx]=255;bytes[idx+1]=255;bytes[idx+2]=255;bytes[idx+3]=alpha;
        }
        pos+=(len+1)/2;
    }
    if(at!=rgba.size())return nullptr;
    SDL_Texture* texture=SDL_CreateTexture(renderer,SDL_PIXELFORMAT_RGBA32,
        SDL_TEXTUREACCESS_STATIC,w,h);
    if(!texture)return nullptr;
    if(!SDL_UpdateTexture(texture,nullptr,rgba.data(),w*4)){
        SDL_DestroyTexture(texture);return nullptr;
    }
    SDL_SetTextureBlendMode(texture,SDL_BLENDMODE_BLEND);
    SDL_SetTextureScaleMode(texture,SDL_SCALEMODE_LINEAR);
    cache.texture=texture;
    return texture;
}
inline const dusk_font_assets::Glyph& glyph(unsigned char c,bool bold) {
    c=(c>=32&&c<127)?c:static_cast<unsigned char>('?');
    return dusk_font_assets::kGlyphs[(bold?95:0)+c-32];
}
inline float measure(const char* s,float px,bool bold=false) {
    if(!s)return 0;
    float w=0;int limit=0;
    for(const unsigned char* p=reinterpret_cast<const unsigned char*>(s);*p&&limit++<512;p++)
        w+=glyph(*p,bold).advance*px/dusk_font_assets::kEmPx;
    return w;
}
inline void draw(SDL_Renderer* r,float x,float y,const char* s,
                 float px,Color color=white,bool bold=false,float maxwidth=0) {
    if(!s || px<1) return;
    auto* texture=ensure(r);
    if(!texture) return;
    SDL_SetTextureColorMod(texture,color.r,color.g,color.b);
    SDL_SetTextureAlphaMod(texture,color.a);
    float scale=px/dusk_font_assets::kEmPx;
    const float start=x;
    const float baseline=y+px*0.87f;
    bool ellipsis=false;
    size_t n=0;
    for(const unsigned char* p=reinterpret_cast<const unsigned char*>(s);*p && n++<256;p++) {
        const auto& g=glyph(*p,bold);
        if(maxwidth>0 && x-start+(float(g.advance)+float(12)*3)*scale>maxwidth && p[1]) {
            ellipsis=true;break;
        }
        if(g.w>0 && g.h>0 && *p!=' ') {
            SDL_FRect src{float(g.x),float(g.y),float(g.w),float(g.h)};
            SDL_FRect dst{x+float(g.left)*scale,baseline+float(g.top)*scale,
                          float(g.w)*scale,float(g.h)*scale};
            SDL_RenderTexture(r,texture,&src,&dst);
        }
        x+=g.advance*scale;
    }
    if(ellipsis) {
        const auto& dot=glyph('.',bold);
        for(int i=0;i<3;i++) {
            SDL_FRect src{float(dot.x),float(dot.y),float(dot.w),float(dot.h)};
            SDL_FRect dst{x+dot.left*scale,baseline+dot.top*scale,
                          dot.w*scale,dot.h*scale};
            SDL_RenderTexture(r,texture,&src,&dst);
            x+=dot.advance*scale;
        }
    }
}
} // namespace dusk_font