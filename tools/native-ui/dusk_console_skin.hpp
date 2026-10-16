#pragma once
// Dusk console skin v0.31: image-reference-led authored pixel chrome.
// Rendered with SDL3 GPU geometry rather than oversized source PNGs:
// every bevel, icon, and preview has precise integer coordinates and scales.
// This header is included after dusk_material_renderer.hpp, and only paints
// presentation. All saved settings, ROM-side localization and inputs remain
// under the existing Dusk host controller.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <string>
namespace dusk_console {
using dusk_native::Rect;
using dusk_material::Rgb;
inline constexpr Rgb void_black{5,6,28}, navy{8,12,44}, rail{12,12,54},
    line{64,53,139}, line_hi{118,91,217}, lilac{180,171,255},
    ivory{238,235,255}, gold{255,232,93}, aqua{104,183,252},
    blue{94,147,240}, blue_shade{47,73,170};
inline int P(float v,float s){return std::max(1,int(std::lround(v*s)));}
inline void block(SDL_Renderer* r,Rect b,Rgb c){
    if(b.w>0&&b.h>0)dusk_material::rect(r,b,c);
}
inline void polygon(SDL_Renderer* r,Rect b,int cut,Rgb tint) {
    if(b.w<1||b.h<1)return;
    cut=std::clamp(cut,0,std::min(b.w,b.h)/3);
    const SDL_FColor fc{tint.r/255.f,tint.g/255.f,tint.b/255.f,tint.a/255.f};
    const SDL_FPoint p[8] = {
      {float(b.x+cut),float(b.y)},{float(b.x+b.w-cut),float(b.y)},
      {float(b.x+b.w),float(b.y+cut)},{float(b.x+b.w),float(b.y+b.h-cut)},
      {float(b.x+b.w-cut),float(b.y+b.h)},{float(b.x+cut),float(b.y+b.h)},
      {float(b.x),float(b.y+b.h-cut)},{float(b.x),float(b.y+cut)}
    };
    SDL_Vertex vertices[18]{};
    for(int i=0;i<6;i++){
        vertices[i*3+0]={p[0],fc,{0.f,0.f}};
        vertices[i*3+1]={p[i+1],fc,{0.f,0.f}};
        vertices[i*3+2]={p[i+2],fc,{0.f,0.f}};
    }
    SDL_SetRenderDrawBlendMode(r,SDL_BLENDMODE_BLEND);
    SDL_RenderGeometry(r,nullptr,vertices,18,nullptr,0);
}
// An asymmetric 3-level bevel adds the missing metallic depth in the prior
// flat "software" version, including consistently trimmed diagonal corners.
inline void bezel(SDL_Renderer* r,Rect b,int cut,Rgb outer,Rgb mid,Rgb inner,float s){
    polygon(r,b,cut,outer);
    int k=P(2,s);
    polygon(r,{b.x+k,b.y+k,b.w-2*k,b.h-2*k},std::max(0,cut-k),mid);
    k=P(4,s);
    polygon(r,{b.x+k,b.y+k,b.w-2*k,b.h-2*k},std::max(0,cut-k),inner);
    const int stroke=P(2,s);
    block(r,{b.x+cut,b.y,b.w-2*cut,stroke},outer);
    block(r,{b.x+cut+stroke,b.y+stroke,b.w-2*cut-2*stroke,stroke},{189,151,255,130});
}
inline void gloss(SDL_Renderer* r,Rect b,float s){
    const int t=P(2,s);
    block(r,{b.x+P(8,s),b.y+P(7,s),std::max(1,b.w-P(16,s)),t},{182,161,248,75});
    block(r,{b.x+P(7,s),b.y+b.h-P(9,s),std::max(1,b.w-P(15,s)),t},{8,4,33,200});
}
inline void corners(SDL_Renderer* r,Rect b,bool active,float s){
    const int d=P(16,s),t=P(5,s);
    const Rgb c=active?gold:Rgb{141,113,235};
    block(r,{b.x,b.y+P(6,s),t,d},c);
    block(r,{b.x+P(6,s),b.y,d,t},c);
    block(r,{b.x+b.w-t,b.y+P(6,s),t,d},c);
    block(r,{b.x+b.w-P(6,s)-d,b.y,d,t},c);
    block(r,{b.x,b.y+b.h-P(6,s)-d,t,d},c);
    block(r,{b.x+P(6,s),b.y+b.h-t,d,t},c);
    block(r,{b.x+b.w-t,b.y+b.h-P(6,s)-d,t,d},c);
    block(r,{b.x+b.w-P(6,s)-d,b.y+b.h-t,d,t},c);
}
inline void caption(SDL_Renderer* r,int x,int y,const char* value,int px,
                    Rgb tint=ivory,bool strong=false,int maxwidth=0){
    dusk_material::label(r,x,y,value,px,tint,strong,maxwidth);
}
inline void midcaption(SDL_Renderer* r,Rect b,const char* value,int px,
                       Rgb tint=ivory,bool strong=false){
    dusk_material::center_label(r,b,value,px,tint,strong);
}
// Explicit 16x16 glyph bitmaps are generated locally, not web/downloaded icons.
// Crisp at every game resolution, including >2x display scale.
inline void glyph(SDL_Renderer* r,int x,int y,int kind,int scale,Rgb tint){
    static constexpr std::array<std::array<const char*,16>,4> shapes{{
      {"................","................","..############..","..#..........#..","..#..........#..","..#..........#..","..#..........#..","..#..........#..","..#..........#..","..#..........#..","..############..",".......##.......",".......##.......",".....######.....","................","................"},
      {"................","....########....","...##......##...","..##........##..","..##........##..","..##...##...##..","..##..####..##..","..##..####..##..","..##...##...##..","..##........##..","...##......##...","....########....","................","................","................","................"},
      {"................","................",".....######.....","...##########...","..############..",".###........###.",".##..##...##.##.",".##.####.####.##",".##..##...##.##",".###........###.","..############..","...##..##..##...","....##....##....","................","................","................"},
      {"................","......####......","...##########...","...##########...","..###..##..###..",".###...##...###.",".###.######.###.","###.########.###","###.########.###",".###.######.###.",".###...##...###.","..###..##..###..","...##########...","...##########...","......####......","................"}
    }};
    if(kind<0||kind>3||scale<1)return;
    const auto& art=shapes[kind];
    for(int row=0;row<16;row++){
        const char* line=art[row];
        for(int col=0;col<16;){
            if(line[col]!='#'){col++;continue;}
            int last=col+1;
            while(last<16&&line[last]=='#')last++;
            block(r,{x+col*scale,y+row*scale,(last-col)*scale,scale},tint);
            col=last;
        }
    }
}
inline void chevron(SDL_Renderer* r,int cx,int cy,bool right,Rgb c,float s){
    const int px=P(3,s);
    for(int i=0;i<4;i++){
        int xx=cx+(right?i*px:-i*px);
        block(r,{xx,cy+(i-2)*px,px,px*2},c);
    }
}
inline void digital_grid(SDL_Renderer* r,Rect b,float s){
    const int step=P(30,s),width=P(1,s);
    // Faint background pixel grid that matches the screenshot without
    // making labels unreadable; this draws ~75 GPU rects, not a texture scan.
    for(int x=b.x+step;x<b.x+b.w;x+=step)
        block(r,{x,b.y,width,b.h},{47,42,104,47});
    for(int y=b.y+step;y<b.y+b.h;y+=step)
        block(r,{b.x,y,b.w,width},{48,47,108,48});
    for(int y=b.y+P(9,s);y<b.y+b.h;y+=step*3)
        for(int x=b.x+P(13,s);x<b.x+b.w;x+=step*5)
            block(r,{x,y,P(3,s),P(3,s)},{85,59,186,75});
}
inline void watermark(SDL_Renderer* r,Rect b,float s){
    if(b.w<P(80,s)||b.h<P(80,s))return;
    // Stylized Digivice / digital crest: polygonal concentric pixel-rings.
    Rect a{b.x+P(12,s),b.y+P(12,s),b.w-P(24,s),b.h-P(24,s)};
    polygon(r,a,P(36,s),{51,32,126,90});
    polygon(r,{a.x+P(19,s),a.y+P(19,s),a.w-P(38,s),a.h-P(38,s)},P(26,s),{10,10,49});
    polygon(r,{a.x+P(36,s),a.y+P(36,s),a.w-P(72,s),a.h-P(72,s)},P(17,s),{64,44,164,85});
    polygon(r,{a.x+a.w/2-P(12,s),a.y+a.h/2-P(12,s),P(24,s),P(24,s)},P(7,s),{14,10,52});
    block(r,{a.x+P(14,s),a.y-P(7,s),P(18,s),P(7,s)},{56,32,144,80});
    block(r,{a.x+a.w-P(32,s),a.y+a.h,P(18,s),P(7,s)},{56,32,144,80});
}
inline void frame(SDL_Renderer* r,const dusk_modern::View& v,
                  const dusk_native::Geometry& geo,float s){
    block(r,{0,0,geo.play.w,geo.play.h},{2,2,23,218});
    Rect b=v.panel;
    polygon(r,{b.x+P(11,s),b.y+P(12,s),b.w,b.h},P(17,s),{0,0,10,160});
    bezel(r,b,P(18,s),{162,126,251},{46,23,105},void_black,s);
    // Edge highlights and extra asymmetric console shoulders.
    block(r,{b.x+P(20,s),b.y+P(5,s),P(108,s),P(5,s)},{131,111,231});
    block(r,{b.x+P(116,s),b.y+P(8,s),P(267,s),P(2,s)},{81,50,183});
    block(r,{b.x+b.w-P(322,s),b.y+P(8,s),P(185,s),P(3,s)},{78,62,166});
    block(r,{b.x+P(4,s),b.y+P(151,s),P(5,s),P(411,s)},{67,44,166});
    block(r,{b.x+b.w-P(9,s),b.y+P(94,s),P(4,s),P(606,s)},{91,58,188});
    // Header band intentionally differs from content, like DS-era game menus.
    Rect header{b.x+P(9,s),b.y+P(7,s),b.w-P(18,s),P(85,s)};
    bezel(r,header,P(14,s),{157,116,246},{53,25,125},{27,16,88},s);
    block(r,{header.x+P(115,s),header.y+P(8,s),P(4,s),header.h-P(16,s)},{126,80,224,100});
    block(r,{header.x+P(121,s),header.y+P(11,s),P(480,s),P(2,s)},{116,84,211});
    block(r,{header.x+P(631,s),header.y+P(20,s),P(468,s),P(2,s)},{65,49,157});
    // Pixel-circuit markings in otherwise empty header chrome.
    for(int i=0;i<10;i++)
        block(r,{header.x+header.w-P(340,s)+i*P(14,s),
                 header.y+P(32,s),P(8,s),P(8,s)},{100,66,204,uint8_t(30+(i%3)*27)});
    for(int i=0;i<7;i++)
        block(r,{header.x+header.w-P(164,s)+i*P(12,s),
                 header.y+P(61,s),P(5,s),P(5,s)},{120,72,193,75});
    // Wide screen: narrow rail with watermark. Mobile: one continuous content field.
    const bool vertical=v.tabs[0].y!=v.tabs[1].y;
    Rect content_area=vertical
        ?Rect{b.x+P(326,s),b.y+P(97,s),b.w-P(338,s),b.h-P(166,s)}
        :Rect{b.x+P(13,s),b.y+P(91,s),b.w-P(26,s),b.h-P(160,s)};
    block(r,content_area,{6,8,36});
    digital_grid(r,content_area,s);
    if(vertical){
        Rect left{b.x+P(15,s),b.y+P(97,s),P(311,s),b.h-P(164,s)};
        block(r,left,rail);digital_grid(r,left,s);
        block(r,{left.x+left.w-P(2,s),left.y,P(2,s),left.h},{69,47,166});
        if(left.h>P(350,s))
            watermark(r,{left.x+P(5,s),left.y+left.h-P(242,s),P(278,s),P(216,s)},s);
    }
    // Metallic framed footer rail aligned to screenshot (~65px tall).
    Rect foot{b.x+P(6,s),v.footer.y,b.w-P(12,s),P(65,s)};
    bezel(r,foot,P(13,s),{148,104,236},{55,26,129},{30,18,93},s);
    block(r,{foot.x+P(150,s),foot.y+P(2,s),P(280,s),P(3,s)},{145,98,246});
    block(r,{foot.x+foot.w-P(316,s),foot.y+foot.h-P(8,s),P(259,s),P(4,s)},{103,62,212});
    for(int i=0;i<15;i++)block(r,{foot.x+foot.w-P(202,s)+P(10,s)*i,
            foot.y+P(18+(i%2)*6,s),P(6,s),P(5,s)},{117,69,226,65});
}
inline void backplate_icon(SDL_Renderer* r,Rect box,Rgb selected,float s){
    polygon(r,box,P(10,s),{30,22,91});
    polygon(r,{box.x+P(3,s),box.y+P(3,s),box.w-P(6,s),box.h-P(6,s)},
            P(7,s),selected);
}
inline void nav(SDL_Renderer* r,const dusk_modern::View& v,float s){
    const bool vertical=v.tabs[0].y!=v.tabs[1].y;
    for(int i=0;i<4;i++){
        Rect b=v.tabs[i];
        const bool active=dusk_modern::state.tab==i;
        const Rgb border=active?Rgb{255,228,109}:Rgb{97,82,195};
        const Rgb inner=active?Rgb{83,48,185}:Rgb{16,17,65};
        bezel(r,b,P(9,s),border,active?Rgb{92,55,202}:Rgb{39,31,104},inner,s);
        gloss(r,b,s);
        if(active){
            block(r,{b.x+P(4,s),b.y+P(9,s),P(10,s),b.h-P(18,s)},gold);
            block(r,{b.x+b.w-P(10,s),b.y+P(10,s),P(5,s),b.h-P(20,s)},gold);
            chevron(r,b.x+P(20,s),b.y+b.h/2,true,{53,26,100},s);
        }
        int pixel=P(vertical?2.25f:1.7f,s),gw=16*pixel;
        int ix=b.x+P(vertical?33.f:15.f,s),iy=b.y+(b.h-gw)/2;
        if(!vertical){ix=b.x+(b.w-gw)/2;iy=b.y+P(8,s);}
        glyph(r,ix,iy,i,pixel,active?ivory:Rgb{168,153,239});
        const char* key[]={"screens","video","controls","system"};
        const char* name=dusk_localization::ui(key[i],dusk_localization::active_language);
        const int font=std::max(11,P(vertical?21.f:12.f,s));
        if(vertical)caption(r,b.x+P(105,s),b.y+(b.h-font)/2,name,font,
                            ivory,active,b.w-P(122,s));
        else midcaption(r,{b.x+P(2,s),b.y+b.h-P(25,s),b.w-P(4,s),P(24,s)},
                        name,font,ivory,active);
    }
}
inline void header(SDL_Renderer* r,const dusk_modern::View& v,float s){
    Rect b=v.panel;
    // Header's mechanical gear is drawn from a repeatable 16x16 asset stencil.
    const bool compact=v.tabs[0].y==v.tabs[1].y;
    Rect seal{b.x+P(compact?15:29,s),b.y+P(18,s),P(compact?49:63,s),P(compact?49:58,s)};
    bezel(r,seal,P(14,s),{132,110,240},{38,18,101},{13,8,54},s);
    glyph(r,seal.x+P(7,s),seal.y+P(7,s),3,P(compact?2:3,s),{198,173,255});
    const auto language=dusk_localization::active_language;
    const char* t=language==dusk_localization::Language::portuguese?"CONFIGURAÇÕES":
                   language==dusk_localization::Language::spanish?"CONFIGURACIÓN":
                   "SETTINGS";
    const bool narrow=v.tabs[0].y==v.tabs[1].y;
    caption(r,b.x+P(narrow?82:135,s),b.y+P(narrow?31:27,s),
            narrow?dusk_localization::ui("settings",language):t,
            P(narrow?23:35,s),ivory,true,
            std::max(60,v.close.x-b.x-P(narrow?90:148,s)));
    bezel(r,v.close,P(9,s),{191,171,251},{49,33,121},{16,13,70},s);
    midcaption(r,v.close,"X",P(28,s),ivory,true);
}
inline void section(SDL_Renderer* r,int x,int y,int width,const char* name,float s){
    // Separately cap the title with a kinked metallic underline.
    int tw=std::min(width-P(42,s),int(dusk_font::measure(name,float(P(20,s)),true))+P(54,s));
    tw=std::max(tw,P(180,s));
    Rect title{x,y,tw,P(39,s)};
    polygon(r,title,P(9,s),{80,97,192});
    polygon(r,{title.x+P(3,s),title.y+P(3,s),title.w-P(6,s),title.h-P(6,s)},
            P(6,s),{12,25,71});
    block(r,{x+P(10,s),y+P(8,s),P(8,s),P(24,s)},gold);
    caption(r,x+P(30,s),y+P(8,s),name,P(19,s),ivory,true,tw-P(35,s));
    block(r,{x+tw,y+P(28,s),std::max(0,width-tw),P(2,s)},{66,86,186});
}
inline void monitor(SDL_Renderer* r,Rect b,float s){
    if(b.w<5||b.h<5)return;
    polygon(r,b,P(4,s),{122,173,255});
    polygon(r,{b.x+P(3,s),b.y+P(3,s),b.w-P(6,s),b.h-P(6,s)},P(3,s),{20,44,118});
    polygon(r,{b.x+P(6,s),b.y+P(6,s),b.w-P(12,s),b.h-P(12,s)},P(2,s),blue);
    block(r,{b.x+P(7,s),b.y+P(7,s),std::max(1,b.w-P(14,s)),P(3,s)},{175,192,255,160});
    block(r,{b.x+P(7,s),b.y+b.h-P(12,s),std::max(1,b.w-P(14,s)),P(3,s)},{27,84,175,150});
}
inline void preview(SDL_Renderer* r,Rect b,int mode,float s){
    // Match approved miniature screen proportions and lavender/blue outlines.
    const int gap=P(8,s);
    if(mode==2) {
        const int ww=b.w*69/100,hh=(b.h-gap)/2;
        monitor(r,{b.x+(b.w-ww)/2,b.y,ww,hh},s);
        monitor(r,{b.x+(b.w-ww)/2,b.y+hh+gap,ww,hh},s);
    }else if(mode==3) {
        const int ww=(b.w-gap)/2;
        monitor(r,{b.x,b.y,ww,b.h},s);
        monitor(r,{b.x+ww+gap,b.y,ww,b.h},s);
    }else{
        monitor(r,b,s);
        if(mode==0||mode==1||mode==5){
            int w=b.w*34/100,h=b.h*40/100;
            const int xx=mode==1?b.x+gap:b.x+b.w-w-gap;
            const int yy=mode==0?b.y+gap:b.y+b.h-h-gap;
            polygon(r,{xx-P(4,s),yy-P(4,s),w+P(8,s),h+P(8,s)},
                    P(4,s),{12,12,69});
            monitor(r,{xx,yy,w,h},s);
        }
    }
}
inline void selected_arrow(SDL_Renderer* r,Rect b,float s){
    const int q=P(7,s),cy=b.y+b.h/2;
    block(r,{b.x+b.w+P(7,s),cy-q,q,q*2},gold);
    chevron(r,b.x+b.w+P(8,s),cy,true,gold,s);
}
inline const char* preset_name(int v){
    static constexpr const char* n[]={"Moderno","Flutuante","Clássico",
                                      "Lado a lado","Somente principal","Foco + PiP"};
    return v>=0&&v<6?n[v]:"";
}
inline void layout_card(SDL_Renderer* r,Rect b,int preset,bool focused,
                        bool chosen,float s){
    const Rgb rim=focused?gold:(chosen?Rgb{145,120,253}:Rgb{75,75,162});
    bezel(r,b,P(11,s),rim,{38,36,118},{24,28,87},s);
    block(r,{b.x+P(4,s),b.y+b.h-P(32,s),b.w-P(8,s),P(26,s)},{26,25,78});
    Rect screen{b.x+P(18,s),b.y+P(13,s),
                b.w-P(36,s),std::max(24,b.h-P(53,s))};
    preview(r,screen,preset,s);
    const int size=std::max(11,P(18,s));
    midcaption(r,{b.x+P(4,s),b.y+b.h-P(33,s),b.w-P(8,s),P(28,s)},
               preset_name(preset),size,ivory,focused||chosen);
    if(focused){corners(r,b,true,s);selected_arrow(r,b,s);}
    else if(chosen){corners(r,b,false,s);}
}
inline std::string row_value(const FrontendPresentation& p,int id){
    auto lang=dusk_localization::active_language;
    if(id==10)return std::string(dusk_localization::name(lang));
    switch(id){
      case 1:return p.dusk.cfg.focus_top?"Superior":"Inferior / Touch";
      case 2:return p.dusk.cfg.auxiliary?"Visível":"Minimizada";
      case 4:return p.dusk.cfg.fill_wide?"16:9 esticado":"Original 4:3";
      case 5:return p.dusk.cfg.fullscreen?"Tela cheia":"Janela";
      case 6:return p.dusk.cfg.half_present?"30 FPS":"60 FPS";
      default:return dusk_value(p,id);
    }
}
inline const char* row_label(int id){
    switch(id){
        case 1:return "Tela principal";
        case 2:return "Tela auxiliar";
        case 3:return "Tamanho da tela auxiliar";
        case 7:return "Posição da PiP";
        case 4:return "Proporção da tela";
        case 5:return "Modo de janela";
        case 6:return "FPS de apresentação";
        case 10:return dusk_localization::ui("language",dusk_localization::active_language);
        default:return "";
    }
}
inline void option_row(SDL_Renderer* r,Rect b,const FrontendPresentation& p,
                       const dusk_modern::Item& item,bool focus,float s){
    const Rgb rim=focus?gold:Rgb{81,81,165};
    bezel(r,b,P(6,s),rim,{32,33,112},{19,23,81},s);
    gloss(r,b,s);
    if(item.kind==1){
        const int value_x=b.x+int(float(b.w)*0.66f);
        const int arrow_width=P(39,s);
        const char* title=row_label(item.value);
        caption(r,b.x+P(17,s),b.y+P(13,s),title,P(17,s),ivory,focus,
                std::max(25,value_x-b.x-P(31,s)));
        polygon(r,{value_x,b.y+P(4,s),b.w-(value_x-b.x)-P(6,s),
                    b.h-P(8,s)},P(7,s),{12,14,60});
        block(r,{value_x,b.y+P(6,s),P(2,s),b.h-P(12,s)},{94,78,167});
        chevron(r,value_x+P(27,s),b.y+b.h/2,false,gold,s);
        chevron(r,b.x+b.w-P(25,s),b.y+b.h/2,true,gold,s);
        std::string value=row_value(p,item.value);
        Rect val{value_x+arrow_width,b.y+P(4,s),
                 std::max(1,b.x+b.w-value_x-arrow_width*2),b.h-P(8,s)};
        midcaption(r,val,value.c_str(),std::max(11,P(16,s)),ivory);
        if(item.value==10 &&
           dusk_localization::active_language!=dusk_localization::Language::english) {
            // Communicate real partial coverage without obscuring input controls.
            const auto *notice=dusk_localization::ui("bridge_notice",dusk_localization::active_language);
            caption(r,b.x+P(17,s),b.y+b.h-P(17,s),notice,std::max(10,P(11,s)),
                    {186,174,225},false,std::max(20,value_x-b.x-P(24,s)));
        }
    }else{
        const bool resume=item.value==8;
        const auto lang=dusk_localization::active_language;
        caption(r,b.x+P(21,s),b.y+P(13,s),
                dusk_localization::ui(resume?"resume":"quit",lang),
                P(18,s),ivory,true,b.w-P(44,s));
        caption(r,b.x+P(21,s),b.y+P(40,s),
                dusk_localization::ui(resume?"return":"confirm_quit",lang),
                std::max(10,P(13,s)),lilac,false,b.w-P(44,s));
    }
}
inline void footer(SDL_Renderer* r,const dusk_modern::View& v,float s){
    const Rect b=v.footer;
    int x=b.x+P(16,s),y=b.y+P(18,s);
    const int badge=P(32,s);
    polygon(r,{x,y,badge,badge},P(9,s),{182,181,254});
    midcaption(r,{x,y,badge,badge},"B",P(19,s),{21,14,74},true);
    caption(r,x+P(48,s),y+P(4,s),"Voltar",P(18,s),ivory);
    x+=P(145,s);
    polygon(r,{x,y,badge,badge},P(9,s),{182,181,254});
    midcaption(r,{x,y,badge,badge},"A",P(19,s),{21,14,74},true);
    caption(r,x+P(48,s),y+P(4,s),"Selecionar",P(18,s),ivory);
    if(b.w>P(650,s)){
        x+=P(177,s);
        // Four-direction pad uses crisp simple cross.
        block(r,{x+P(9,s),y,P(10,s),P(32,s)},{195,182,252});
        block(r,{x,y+P(10,s),P(28,s),P(10,s)},{195,182,252});
        block(r,{x+P(12,s),y+P(12,s),P(4,s),P(4,s)},{48,29,102});
        caption(r,x+P(44,s),y+P(4,s),"Navegar",P(18,s),ivory);
    }
}
inline void render(SDL_Renderer* r,const FrontendPresentation& p,
                   const dusk_native::Geometry& geo){
    const dusk_modern::View v=dusk_modern::calculate(geo,p);
    const bool narrow=v.tabs[0].y==v.tabs[1].y;
    const float s=narrow
       ?std::clamp(std::min(float(std::max(1,geo.play.w))/390.f,
                            float(std::max(1,geo.play.h))/750.f),0.70f,1.15f)
       :float(v.panel.w)/1250.f;
    if(v.panel.w<120||v.panel.h<150)return;
    frame(r,v,geo,s);
    header(r,v,s);
    nav(r,v,s);
    if(dusk_modern::state.tab!=2){
        const SDL_Rect clip{v.content.x,v.content.y,v.content.w,v.content.h};
        SDL_SetRenderClipRect(r,&clip);
        if(dusk_modern::state.tab==0) {
            section(r,v.content.x,v.content.y+P(1,s)-dusk_modern::state.scroll,
                    v.content.w,"Modo de Exibição",s);
            if(v.count>6){
                section(r,v.content.x,v.items[6].rect.y-P(53,s),v.content.w,
                        "Opções do modo selecionado",s);
            }
        }else if(dusk_modern::state.tab==1){
            section(r,v.content.x,v.content.y+P(1,s)-dusk_modern::state.scroll,
                    v.content.w,"Vídeo e Exibição",s);
        }else{
            section(r,v.content.x,v.content.y+P(1,s)-dusk_modern::state.scroll,
                    v.content.w,"Sistema",s);
        }
        for(int i=0;i<v.count;i++){
            const dusk_modern::Item item=v.items[i];
            const Rect b=item.rect;
            if(b.y+b.h<=v.content.y||b.y>=v.content.y+v.content.h)continue;
            const bool focus=dusk_modern::state.focus==i;
            const bool chosen=item.kind==0&&int(p.dusk.cfg.layout)==item.value;
            if(item.kind==0)layout_card(r,b,item.value,focus,chosen,s);
            else option_row(r,b,p,item,focus,s);
        }
        SDL_SetRenderClipRect(r,nullptr);
    } else {
        section(r,v.content.x,v.content.y+P(1,s),v.content.w,
                "Jogue do seu jeito",s);
        const char* names[]={"Teclado","Controle","Mouse","Touch"};
        const char* help[]={"Setas / Enter / Esc / Tab",
                            "Direcional / A / B / Select / LB / RB",
                            "Clique / Roda / Arraste",
                            "Toque / Deslize / Arraste"};
        const int row=P(85,s),start=v.content.y+P(57,s);
        const SDL_Rect clip{v.content.x,v.content.y,v.content.w,v.content.h};
        SDL_SetRenderClipRect(r,&clip);
        for(int i=0;i<4;i++){
            Rect box{v.content.x,start+i*row-dusk_modern::state.scroll,
                     v.content.w,P(75,s)};
            if(box.y+box.h<v.content.y||box.y>v.content.y+v.content.h)continue;
            bezel(r,box,P(8,s),{86,76,174},{25,26,99},{17,20,70},s);
            caption(r,box.x+P(19,s),box.y+P(12,s),names[i],P(19,s),ivory,true,box.w-P(35,s));
            caption(r,box.x+P(19,s),box.y+P(42,s),help[i],P(15,s),lilac,false,box.w-P(35,s));
        }
        SDL_SetRenderClipRect(r,nullptr);
    }
    const int maximum=dusk_modern::max_scroll(v);
    if(maximum>0){
        const int th=std::max(P(28,s),v.content.h*v.content.h/std::max(1,v.content_height));
        const int track=std::max(1,v.content.h-P(12,s));
        const int pos=dusk_modern::state.scroll*(track-th)/maximum;
        block(r,{v.content.x+v.content.w-P(5,s),v.content.y+P(6,s)+pos,
                 P(4,s),th},{162,116,243});
    }
    footer(r,v,s);
}
} // namespace dusk_console
namespace dusk_material {
inline void panel(SDL_Renderer* r,const FrontendPresentation& p,
                  const dusk_native::Geometry& g){
    dusk_console::render(r,p,g);
}
} // namespace dusk_material
