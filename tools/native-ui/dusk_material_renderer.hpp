#pragma once
// Material-inspired, DPI-aware, native SDL3 UI: no pixel-font rendering, no OS fonts.
// Uses the already established Dusk input/geometry model and does not touch guest state.
#include "dusk_ui_font.hpp"
#include "dusk_localization.hpp"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <string>
namespace dusk_material {
using dusk_modern::Rect;
using dusk_modern::View;
using dusk_modern::Item;
struct Rgb { uint8_t r,g,b,a=255; };
static constexpr Rgb ink{238,234,254}, secondary{175,170,209},
  accent{188,147,255}, cyan{107,224,247}, background{13,12,35},
  surface{27,23,57}, elevated{36,31,73}, border{68,61,112},
  selected{68,45,119}, dim{7,6,24,205};
inline void rect(SDL_Renderer* r, Rect v, Rgb c) {
    if(v.w<1||v.h<1)return;
    SDL_SetRenderDrawBlendMode(r,SDL_BLENDMODE_BLEND);
    SDL_SetRenderDrawColor(r,c.r,c.g,c.b,c.a);
    SDL_FRect f{float(v.x),float(v.y),float(v.w),float(v.h)};
    SDL_RenderFillRect(r,&f);
}
inline void round(SDL_Renderer* r,Rect b,int rad,Rgb color) {
    if(b.w<=0||b.h<=0)return;
    rad=std::clamp(rad,0,std::min(b.w,b.h)/2);
    if(rad<2){rect(r,b,color);return;}
    rect(r,{b.x+rad,b.y,b.w-2*rad,b.h},color);
    rect(r,{b.x,b.y+rad,rad,b.h-2*rad},color);
    rect(r,{b.x+b.w-rad,b.y+rad,rad,b.h-2*rad},color);
    SDL_FColor col{color.r/255.f,color.g/255.f,color.b/255.f,color.a/255.f};
    constexpr int segments=12;
    for(int corner=0;corner<4;corner++) {
        const float cx=float(b.x+(corner%2 ? b.w-rad:rad));
        const float cy=float(b.y+(corner/2 ? b.h-rad:rad));
        const float base=float(corner==0?2:corner==1?3:corner==2?1:0)*1.570796327f;
        SDL_Vertex vertices[segments*3];
        for(int j=0;j<segments;j++) {
            const float a=base+float(j)*1.570796327f/float(segments);
            const float z=base+float(j+1)*1.570796327f/float(segments);
            vertices[j*3+0]={{cx,cy},col,{0,0}};
            vertices[j*3+1]={{cx+rad*std::cos(a),cy+rad*std::sin(a)},col,{0,0}};
            vertices[j*3+2]={{cx+rad*std::cos(z),cy+rad*std::sin(z)},col,{0,0}};
        }
        // Angles go TL, TR, BL, BR with the center and edges above.
        // The filled strips guarantee seamless corners on fractional DPI.
        SDL_RenderGeometry(r,nullptr,vertices,segments*3,nullptr,0);
    }
}
inline void rr(SDL_Renderer* r,Rect b,int radius,Rgb color,Rgb outline={0,0,0,0}) {
    if(outline.a){round(r,b,radius,outline);b={b.x+1,b.y+1,b.w-2,b.h-2};radius=std::max(0,radius-1);}
    round(r,b,radius,color);
}
inline float scale(const View& v){return std::clamp(float(v.panel.w)/900.f,0.75f,1.65f);}
inline int dp(float points,float s){return std::max(1,int(std::lround(points*s)));}
inline void label(SDL_Renderer* r,int x,int y,const char* txt,int px,
                  Rgb c=ink,bool bold=false,int max_width=0){
    if(!txt)return;
    dusk_font::draw(r,float(x),float(y),txt,float(px),
        {c.r,c.g,c.b,c.a},bold,float(max_width));
}
inline void center_label(SDL_Renderer* r,Rect b,const char* txt,int px,Rgb c=ink,bool bold=false){
    const float len=dusk_font::measure(txt,float(px),bold);
    int x=b.x+std::max(6,int((b.w-len)/2.f));
    label(r,x,b.y+std::max(2,(b.h-px)/2),txt,px,c,bold,std::max(10,b.w-12));
}
inline void circle(SDL_Renderer* r,int x,int y,int rad,Rgb c){round(r,{x-rad,y-rad,rad*2,rad*2},rad,c);}
inline const char* layout_name(int i){
    constexpr const char* n[] = {"Modern", "Floating", "Classic", "Side by side", "Main only", "Focus + PiP"};
    return i>=0&&i<6?n[i]:"";
}
inline const char* tab_name(int i){
    constexpr const char* k[]={"screens","video","controls","system"};
    return i>=0&&i<4 ? dusk_localization::ui(k[i],dusk_localization::active_language):"";
}
inline void mini_display(SDL_Renderer* r,Rect b,Rgb tone) {
    rr(r,b,dp(6,1.f),tone);
    rr(r,{b.x+3,b.y+3,b.w-6,b.h-6},3,{40,43,105});
    rr(r,{b.x+7,b.y+7,std::max(1,b.w-14),std::max(1,b.h-14)},2,{84,86,170});
}
inline void preview(SDL_Renderer* r,Rect b,int i,bool active,float s){
    rr(r,b,dp(9,s),{19,17,50});
    const int margin=dp(9,s),gap=dp(5,s);
    Rect inner{b.x+margin,b.y+margin,b.w-2*margin,b.h-2*margin};
    if(i==2) {
        const int ah=(inner.h-gap)/2;
        mini_display(r,{inner.x+inner.w/6,inner.y,inner.w*2/3,ah},{91,76,170});
        mini_display(r,{inner.x+inner.w/6,inner.y+ah+gap,inner.w*2/3,ah},{126,73,166});
    } else if(i==3) {
        const int aw=(inner.w-gap)/2;
        mini_display(r,{inner.x,inner.y,aw,inner.h},{91,76,170});
        mini_display(r,{inner.x+aw+gap,inner.y,aw,inner.h},{126,73,166});
    } else {
        mini_display(r,inner,{91,76,170});
        if(i==0||i==1||i==5) {
            int ww=std::max(18,inner.w*35/100), hh=std::max(15,inner.h*41/100);
            int xx=(i==1?inner.x+gap:inner.x+inner.w-ww-gap);
            int yy=(i==0?inner.y+gap:inner.y+inner.h-hh-gap);
            mini_display(r,{xx,yy,ww,hh},{152,99,195});
        }
    }
    if(active)round(r,{b.x+b.w-dp(20,s),b.y+dp(9,s),dp(9,s),dp(9,s)},dp(5,s),cyan);
}
inline void legacy_panel(SDL_Renderer* r,const FrontendPresentation& p,
                  const dusk_native::Geometry& geo){
    View v=dusk_modern::calculate(geo,p);
    float s=scale(v);
    int hpx=dp(24,s), bpx=dp(17,s), mpx=dp(14,s);
    rect(r,{0,0,geo.play.w,geo.play.h},dim);
    rr(r,{v.panel.x+4,v.panel.y+dp(8,s),v.panel.w,v.panel.h},dp(24,s),{0,0,0,70});
    rr(r,v.panel,dp(23,s),background,{90,76,137,255});
    // Accent is confined to header and is never behind text.
    rr(r,{v.panel.x+dp(18,s),v.panel.y+dp(18,s),dp(5,s),dp(37,s)},dp(3,s),accent);
    // One clear heading; align it vertically with the left accent bar.
    label(r,v.title.x+dp(11,s),v.title.y+dp(17,s),dusk_localization::ui("settings",dusk_localization::active_language),hpx,ink,true,
          std::max(20,v.close.x-v.title.x-dp(40,s)));
    rr(r,v.close,dp(13,s),elevated);
    center_label(r,v.close,"X",bpx,ink,true);
    for(int i=0;i<4;i++){
        Rect tab=v.tabs[i];
        const bool active=i==dusk_modern::state.tab;
        rr(r,tab,dp(12,s),active?selected:surface);
        if(active)rr(r,{tab.x+dp(10,s),tab.y+tab.h-dp(4,s),tab.w-dp(20,s),dp(3,s)},dp(2,s),cyan);
        center_label(r,tab,tab_name(i),mpx,active?ink:secondary,active);
    }
    // Scrollbar and cards cannot paint outside the content viewport.
    const SDL_Rect viewport{v.content.x,v.content.y,v.content.w,v.content.h};
    SDL_SetRenderClipRect(r,&viewport);
    for(int i=0;i<v.count;i++){
        auto item=v.items[i];auto b=item.rect;
        if(b.y+b.h<v.content.y || b.y>v.content.y+v.content.h)continue;
        bool focused=dusk_modern::state.focus==i;
        bool chosen=item.kind==0 && int(p.dusk.cfg.layout)==item.value;
        rr(r,b,dp(16,s),chosen?selected:(focused?elevated:surface),
          focused||chosen?Rgb{113,90,192}:Rgb{60,52,101});
        if(item.kind==0){
            int label_h=dp(28,s);
            Rect preview_area{b.x+dp(10,s),b.y+dp(9,s),b.w-dp(20,s),
                              std::max(25,b.h-dp(19,s)-label_h)};
            preview(r,preview_area,item.value,chosen,s);
            label(r,b.x+dp(12,s),b.y+b.h-label_h+dp(3,s),layout_name(item.value),
                  mpx,chosen?ink:secondary,chosen,b.w-dp(24,s));
        } else {
            const char *caption="",*value="";
            std::string backing;
            if(item.kind==1){
                if(item.value==10) {
                    caption=dusk_localization::ui("language",dusk_localization::active_language);
                    backing=std::string(dusk_localization::name(dusk_localization::active_language));
                } else {
                    caption=dusk_label(item.value);
                    backing=dusk_value(p,item.value);
                }
                value=backing.c_str();
            } else {
                const auto language=dusk_localization::active_language;
                caption=dusk_localization::ui(item.value==8?"resume":"quit",language);
                value=dusk_localization::ui(item.value==8?"return":"confirm_quit",language);
            }
            label(r,b.x+dp(17,s),b.y+dp(11,s),caption,bpx,ink,true,b.w-dp(62,s));
            label(r,b.x+dp(17,s),b.y+dp(39,s),value,mpx,secondary,false,b.w-dp(68,s));
            if(item.kind==1 && item.value==10 &&
               dusk_localization::active_language!=dusk_localization::Language::english)
                label(r,b.x+dp(17,s),b.y+dp(61,s),
                      dusk_localization::ui("bridge_notice",dusk_localization::active_language),
                      std::max(9,mpx-3),secondary,false,b.w-dp(68,s));
            if(item.kind==1)center_label(r,{b.x+b.w-dp(43,s),b.y+dp(7,s),dp(32,s),b.h-dp(14,s)},">",bpx,accent,true);
        }
    }
    if(dusk_modern::state.tab==2){
        int x=v.content.x+dp(18,s),y=v.content.y+dp(15,s);
        label(r,x,y,"Play your way",hpx,ink,true,v.content.w-dp(30,s));
        const char *rows[][2]={{"Keyboard","Arrow keys / Enter / Esc"},
                              {"Controller","D-pad / A / B / Select"},
                              {"Mouse","Click / scroll / drag"},
                              {"Touch","Tap / swipe / drag"}};
        int row_h=dp(66,s);
        for(int i=0;i<4;i++){
            Rect b{x,y+dp(50,s)+i*(row_h+dp(8,s)),v.content.w-dp(36,s),row_h};
            rr(r,b,dp(14,s),surface);
            label(r,b.x+dp(15,s),b.y+dp(6,s),rows[i][0],bpx,ink,true,b.w-dp(30,s));
            label(r,b.x+dp(15,s),b.y+dp(33,s),rows[i][1],mpx,secondary,false,b.w-dp(30,s));
        }
    }
    SDL_SetRenderClipRect(r,nullptr);
    if(int maximum=dusk_modern::max_scroll(v);maximum>0){
        const int bar=v.content.h-dp(12,s);
        const int thumb=std::max(dp(30,s),bar*v.content.h/std::max(1,v.content_height));
        int yy=(bar-thumb)*dusk_modern::state.scroll/std::max(1,maximum);
        rr(r,{v.content.x+v.content.w-dp(4,s),v.content.y+dp(6,s)+yy,
              dp(3,s),thumb},dp(2,s),accent);
    }
    rect(r,{v.footer.x,v.footer.y,v.footer.w,1},{65,56,111});
    label(r,v.footer.x+dp(8,s),v.footer.y+dp(16,s),
          v.footer.w<590?"B / Esc  Back":"B / Esc  Back       A / Enter  Select",mpx,secondary,
          false,v.footer.w-dp(20,s));
}
inline void pip(SDL_Renderer* r,const FrontendPresentation& p,
               const dusk_native::Geometry& g){
    if(p.dusk.cfg.layout!=dusk_native::Layout::Focus)return;
    if(g.pip_restore.w>0){
        rr(r,{g.pip_restore.x,g.pip_restore.y,g.pip_restore.w,g.pip_restore.h},12,surface,{82,63,135});
        center_label(r,g.pip_restore,"Show",14,ink,true);return;
    }
    if(g.pip_bar.w<=0)return;
    // Draw over the already-rendered top chrome, do not alter the DS image.
    rr(r,g.pip_bar,8,{20,17,48,248});
    label(r,g.pip_bar.x+9,g.pip_bar.y+5,
          p.dusk.cfg.focus_top?"Touch screen":"Top screen",14,ink,true,
          std::max(24,g.pip_swap.x-g.pip_bar.x-14));
    rr(r,g.pip_swap,6,elevated);
    rr(r,g.pip_minimize,6,elevated);
    center_label(r,g.pip_swap,"<>",13,ink,true);
    center_label(r,g.pip_minimize,"-",17,ink,true);
}
// A GPU-rendered vector cog, rather than text or a DPI-dependent bitmap.
// Eight equal teeth surround an open center, preserving sharpness at any UI scale.
inline void gear_icon(SDL_Renderer* r,Rect bounds,Rgb tint){
    if(bounds.w<18 || bounds.h<18) return;
    constexpr int teeth=8, samples=teeth*6;
    constexpr float tau=6.2831853071795864769f;
    const float cx=float(bounds.x)+float(bounds.w)*0.5f;
    const float cy=float(bounds.y)+float(bounds.h)*0.5f;
    const float outer=std::max(5.f,float(std::min(bounds.w,bounds.h))*0.28f);
    const float inner=outer*0.39f;
    const SDL_FColor color{tint.r/255.f,tint.g/255.f,tint.b/255.f,tint.a/255.f};
    SDL_Vertex vertices[samples*6]{};
    for(int i=0;i<samples;i++){
        const auto point=[&](int j,float radius){
            const float a=tau*float(j)/float(samples)-tau*0.25f;
            return SDL_FPoint{cx+std::cos(a)*radius,cy+std::sin(a)*radius};
        };
        const auto radius=[](int j){
            const int segment=j%6;
            return segment>=2 && segment<=4 ? 1.f : 0.79f;
        };
        const SDL_FPoint p0=point(i,outer*radius(i));
        const SDL_FPoint p1=point(i+1,outer*radius(i+1));
        const SDL_FPoint q0=point(i,inner);
        const SDL_FPoint q1=point(i+1,inner);
        const int o=i*6;
        vertices[o+0]={p0,color,{0,0}};
        vertices[o+1]={p1,color,{0,0}};
        vertices[o+2]={q0,color,{0,0}};
        vertices[o+3]={q0,color,{0,0}};
        vertices[o+4]={p1,color,{0,0}};
        vertices[o+5]={q1,color,{0,0}};
    }
    SDL_RenderGeometry(r,nullptr,vertices,samples*6,nullptr,0);
}
inline void corner(SDL_Renderer* r,const FrontendPresentation& p,
                   const dusk_native::Geometry& g){
    rr(r,g.settings,10,p.dusk.menu_open?selected:surface,{75,67,130});
    gear_icon(r,g.settings,ink);
}
} // namespace dusk_material
// Reference-calibrated Dusk sprite chrome; existing PiP and corner controls stay native.
#include "dusk_console_skin.hpp"
