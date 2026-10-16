#pragma once
// Material-inspired, DPI-aware, native SDL3 UI: no pixel-font rendering, no OS fonts.
// Uses the already established Dusk input/geometry model and does not touch guest state.
#include "dusk_ui_font.hpp"
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
    constexpr const char* t[]={"Screens","Video","Controls","System"};return i>=0&&i<4?t[i]:"";
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
// Angular, light-weight vector primitives. Kept in the SDL host layer:
// these are equivalent to SVG paths but have no browser, image scaling or asset dependency.
inline void octagon(SDL_Renderer* r, Rect b, int cut, Rgb color) {
    if(b.w<1||b.h<1)return;
    cut=std::clamp(cut,0,std::min(b.w,b.h)/3);
    const SDL_FColor rgba{color.r/255.f,color.g/255.f,color.b/255.f,color.a/255.f};
    SDL_FPoint p[8]={{float(b.x+cut),float(b.y)},{float(b.x+b.w-cut),float(b.y)},
      {float(b.x+b.w),float(b.y+cut)},{float(b.x+b.w),float(b.y+b.h-cut)},
      {float(b.x+b.w-cut),float(b.y+b.h)},{float(b.x+cut),float(b.y+b.h)},
      {float(b.x),float(b.y+b.h-cut)},{float(b.x),float(b.y+cut)}};
    SDL_Vertex triangles[18]{};
    for(int i=0;i<6;i++){
        triangles[i*3+0]={p[0],rgba,{0,0}};
        triangles[i*3+1]={p[i+1],rgba,{0,0}};
        triangles[i*3+2]={p[i+2],rgba,{0,0}};
    }
    SDL_SetRenderDrawBlendMode(r,SDL_BLENDMODE_BLEND);
    SDL_RenderGeometry(r,nullptr,triangles,18,nullptr,0);
}
inline void bevel(SDL_Renderer* r,Rect b,int cut,Rgb body,Rgb edge){
    octagon(r,b,cut,edge);
    octagon(r,{b.x+2,b.y+2,b.w-4,b.h-4},std::max(0,cut-2),body);
}
inline void ui_line(SDL_Renderer* r,Rect b,Rgb c){rect(r,b,c);}
inline void menu_icon(SDL_Renderer* r, Rect b, int type, Rgb c){
    if(b.w<15||b.h<15)return;
    const int s=std::min(b.w,b.h), x=b.x+(b.w-s)/2,y=b.y+(b.h-s)/2;
    const int t=std::max(2,s/11);
    if(type==0){ // display
        rect(r,{x+2,y+3,s-4,t},c);rect(r,{x+2,y+3,t,s-9},c);
        rect(r,{x+s-2-t,y+3,t,s-9},c);rect(r,{x+2,y+s-6,s-4,t},c);
        rect(r,{x+s/2-t/2,y+s-5,t,4},c);rect(r,{x+s/4,y+s-2,s/2,t},c);
    }else if(type==1){ // motion/video frame
        bevel(r,{x+2,y+4,s-4,s-8},3,{33,28,83},c);
        rect(r,{x+6,y+6,t*2,t},c);rect(r,{x+6,y+s-8,t*2,t},c);
        rect(r,{x+s-9,y+6,t*2,t},c);rect(r,{x+s-9,y+s-8,t*2,t},c);
        octagon(r,{x+s/2-2,y+s/2-4,t*4,t*4},2,c);
    }else if(type==2){ // gamepad shell and physical buttons
        bevel(r,{x+1,y+s/4,s-2,s/2},s/5,c,c);
        rect(r,{x+s/4-1,y+s/2-5,t,10},{31,22,79});
        rect(r,{x+s/4-5,y+s/2-1,10,t},{31,22,79});
        rect(r,{x+s*2/3,y+s/2-3,t*2,t*2},{31,22,79});
        rect(r,{x+s*3/4,y+s/2+3,t*2,t*2},{31,22,79});
    }else if(type==3){ // system gear, twelve simple straight segments
        const int cx=x+s/2,cy=y+s/2,rr=std::max(4,s/3);
        octagon(r,{cx-rr,cy-rr,rr*2,rr*2},rr/3,c);
        for(int i=-1;i<=1;i+=2){rect(r,{cx+i*(rr+1)-2,cy-t,t+3,t*2},c);
            rect(r,{cx-t,cy+i*(rr+1)-2,t*2,t+3},c);}
        octagon(r,{cx-t*2,cy-t*2,t*4,t*4},t,{23,17,66},{23,17,66});
    }else if(type==4){ // opposing arrows
        octagon(r,{x+2,y+s/2-3,6,6},2,c);
        octagon(r,{x+s-8,y+s/2-3,6,6},2,c);
    }
}
inline const char* option_title(int id){
    switch(id){
        case 1:return "Tela principal";
        case 2:return "Tela auxiliar";
        case 3:return "Tamanho da auxiliar";
        case 7:return "Posicao do PiP";
        case 4:return "Proporcao de tela";
        case 5:return "Modo de janela";
        case 6:return "FPS de exibicao";
        default:return "";
    }
}
inline const char* option_value(const FrontendPresentation& p,int id){
    switch(id){
        case 1:return p.dusk.cfg.focus_top?"Superior":"Inferior / Touch";
        case 2:return p.dusk.cfg.auxiliary?"Visivel":"Minimizada";
        case 4:return p.dusk.cfg.fill_wide?"16:9 esticado":"Original 4:3";
        case 5:return p.dusk.cfg.fullscreen?"Tela cheia":"Janela";
        case 6:return p.dusk.cfg.half_present?"30 FPS":"60 FPS";
        default:return nullptr;
    }
}
inline const char* preset_name(int id){
    constexpr const char* t[]={"Moderno","Flutuante","Classico",
                               "Lado a lado","Somente principal","Foco + PiP"};
    return id>=0 && id<6?t[id]:"";
}
inline const char* category_name(int i){
    constexpr const char* t[]={"Telas","Video","Controles","Sistema"};
    return i>=0 && i<4?t[i]:"";
}
inline void console_preview(SDL_Renderer* r,Rect b,int mode,float sc){
    // Miniatures are pure geometry, not copies of the game framebuffer.
    const int gap=dp(5,sc);
    bevel(r,b,dp(5,sc),{14,20,57},{74,73,152});
    Rect area{b.x+gap*2,b.y+gap*2,b.w-gap*4,b.h-gap*4};
    if(area.w<20||area.h<20)return;
    auto disp=[&](Rect rr){
        bevel(r,rr,std::max(2,dp(3,sc)),{72,117,196},{137,154,246});
        rect(r,{rr.x+4,rr.y+4,std::max(1,rr.w-8),std::max(1,rr.h-8)},{79,127,209});
    };
    if(mode==2) {
        Rect rr{area.x+area.w/8,area.y,area.w*3/4,(area.h-gap)/2};
        disp(rr);rr.y+=rr.h+gap;disp(rr);
    }else if(mode==3){
        Rect a{area.x,area.y,(area.w-gap)/2,area.h};
        Rect d{a.x+a.w+gap,a.y,a.w,a.h};disp(a);disp(d);
    }else {
        disp(area);
        if(mode!=4){
            int sw=std::max(12,area.w/3),sh=std::max(10,area.h/3);
            const int xx=mode==1?area.x+gap:area.x+area.w-sw-gap;
            const int yy=mode==0?area.y+gap:area.y+area.h-sh-gap;
            Rect mini{xx,yy,sw,sh};
            bevel(r,mini,2,{98,111,194},{213,174,250});
        }
    }
}
inline void panel(SDL_Renderer* r,const FrontendPresentation& p,
                  const dusk_native::Geometry& geo){
    const View v=dusk_modern::calculate(geo,p);
    const float s=std::clamp(float(v.panel.w)/1160.f,0.83f,1.22f);
    const int title_px=dp(27,s),body_px=dp(15,s),small_px=dp(13,s);
    const int edge=dp(12,s);
    const Rgb bg{9,12,40},base{17,23,66},side{15,20,58},tile{27,33,86},
       lilac{171,153,238},ink2{231,228,255},gold{251,213,84},
       violet{109,74,211},stroke2{81,82,162},bright{157,129,245};
    rect(r,{0,0,geo.play.w,geo.play.h},{3,5,24,207});
    rect(r,{v.panel.x+dp(7,s),v.panel.y+dp(8,s),v.panel.w,v.panel.h},{0,0,0,70});
    bevel(r,v.panel,dp(19,s),bg,bright);
    // Header strip. No procedural neon gradients or blurred glow.
    const Rect hd{v.panel.x+dp(5,s),v.panel.y+dp(5,s),
                  v.panel.w-dp(10,s),dp(74,s)};
    bevel(r,hd,dp(12,s),{37,22,95},{79,64,168});
    rect(r,{hd.x+dp(14,s),hd.y+dp(15,s),dp(5,s),hd.h-dp(30,s)},gold);
    menu_icon(r,{hd.x+dp(30,s),hd.y+dp(18,s),dp(35,s),dp(35,s)},3,lilac);
    label(r,hd.x+dp(77,s),hd.y+dp(21,s),"CONFIGURACOES",title_px,ink2,true,
          std::max(24,v.close.x-hd.x-dp(100,s)));
    bevel(r,v.close,dp(8,s),{36,28,91},bright);
    center_label(r,v.close,"X",dp(23,s),ink2,true);
    const bool stacked=v.tabs[0].y==v.tabs[1].y;
    if(!stacked){
        Rect left{v.panel.x+dp(9,s),v.tabs[0].y-dp(11,s),
                  v.tabs[0].w+dp(18,s),v.footer.y-v.tabs[0].y+dp(3,s)};
        rect(r,left,{11,17,52});
        // A quiet glyph-shaped watermark at the bottom of the navigation rail.
        const Rect mark{left.x+dp(25,s),left.y+left.h-dp(192,s),
                        std::min(left.w-dp(50,s),dp(162,s)),dp(150,s)};
        octagon(r,mark,dp(34,s),{25,23,73});
        octagon(r,{mark.x+dp(30,s),mark.y+dp(28,s),
                   mark.w-dp(60,s),mark.h-dp(55,s)},dp(13,s),{13,17,54});
        octagon(r,{mark.x+mark.w/2-dp(13,s),mark.y+mark.h/2-dp(13,s),
                   dp(26,s),dp(26,s)},dp(8,s),{44,37,108});
    }
    // Real focus is from the shared keyboard/gamepad/mouse/touch state.
    for(int i=0;i<4;i++){
        const Rect t=v.tabs[i];
        const bool active=i==dusk_modern::state.tab;
        bevel(r,t,dp(7,s),active?Rgb{78,48,163}:side,
              active?gold:Rgb{69,66,138});
        if(active){
            rect(r,{t.x+dp(4,s),t.y+dp(5,s),dp(5,s),t.h-dp(10,s)},gold);
        }
        const int iconSize=dp(stacked?19:25,s);
        if(stacked && t.w<110) {
            menu_icon(r,{t.x+(t.w-iconSize)/2,t.y+dp(7,s),iconSize,iconSize},
                      i,active?ink2:lilac);
            center_label(r,{t.x,t.y+t.h-dp(24,s),t.w,dp(22,s)},
                         category_name(i),std::max(10,dp(12,s)),ink2,active);
        }else{
            menu_icon(r,{t.x+dp(18,s),t.y+(t.h-iconSize)/2,iconSize,iconSize},
                      i,active?ink2:lilac);
            label(r,t.x+dp(53,s),t.y+(t.h-body_px)/2,
                  category_name(i),body_px,ink2,active,
                  std::max(10,t.w-dp(65,s)));
        }
    }
    const SDL_Rect clip{v.content.x,v.content.y,v.content.w,v.content.h};
    SDL_SetRenderClipRect(r,&clip);
    if(dusk_modern::state.tab==0){
        label(r,v.content.x+dp(15,s),v.content.y+dp(11,s)-dusk_modern::state.scroll,
              "MODO DE EXIBICAO",body_px,ink2,true,v.content.w-dp(18,s));
        rect(r,{v.content.x+dp(8,s),v.content.y+dp(14,s)-dusk_modern::state.scroll,
                 dp(4,s),dp(15,s)},gold);
        if(v.count>6){
            const int y=v.items[6].rect.y-dp(35,s);
            label(r,v.content.x+dp(15,s),y,"OPCOES DO MODO SELECIONADO",body_px,
                  ink2,true,v.content.w-dp(18,s));
            rect(r,{v.content.x+dp(8,s),y+dp(3,s),dp(4,s),dp(15,s)},gold);
        }
    } else if(dusk_modern::state.tab==1){
        label(r,v.content.x+dp(15,s),v.content.y+dp(11,s)-dusk_modern::state.scroll,
              "VIDEO E EXIBICAO",body_px,ink2,true,v.content.w-dp(18,s));
    }else if(dusk_modern::state.tab==3){
        label(r,v.content.x+dp(15,s),v.content.y+dp(11,s)-dusk_modern::state.scroll,
              "SISTEMA",body_px,ink2,true,v.content.w-dp(18,s));
    }
    for(int i=0;i<v.count;i++){
        const Item item=v.items[i];const Rect b=item.rect;
        if(b.y+b.h<=v.content.y||b.y>=v.content.y+v.content.h)continue;
        const bool focused=dusk_modern::state.focus==i;
        const bool chosen=item.kind==0 && int(p.dusk.cfg.layout)==item.value;
        bevel(r,b,dp(7,s),focused?Rgb{37,35,100}:tile,
              focused?gold:(chosen?bright:stroke2));
        if(item.kind==0){
            const Rect pv{b.x+dp(11,s),b.y+dp(10,s),
                b.w-dp(22,s),std::max(22,b.h-dp(45,s))};
            console_preview(r,pv,item.value,s);
            center_label(r,{b.x+dp(4,s),b.y+b.h-dp(29,s),
                       b.w-dp(8,s),dp(26,s)},preset_name(item.value),
                         std::max(11,small_px),ink2,focused||chosen);
            if(chosen){
                // Permanent selected check, distinct from navigational focus.
                octagon(r,{b.x+b.w-dp(24,s),b.y+dp(4,s),
                           dp(19,s),dp(19,s)},dp(5,s),gold);
                center_label(r,{b.x+b.w-dp(24,s),b.y+dp(1,s),dp(19,s),
                                dp(22,s)},"v",dp(14,s),bg,true);
            }
        }else if(item.kind==1){
            const char* caption=option_title(item.value);
            const char* localized=option_value(p,item.value);
            std::string original=localized?localized:dusk_value(p,item.value);
            int vstart=b.x+std::max(b.w/2,dp(245,s));
            if(vstart>b.x+b.w-dp(126,s))vstart=b.x+b.w-dp(126,s);
            label(r,b.x+dp(16,s),b.y+(b.h-body_px)/2,caption,
                  body_px,ink2,focused,std::max(12,vstart-b.x-dp(20,s)));
            rect(r,{vstart,b.y+dp(8,s),1,b.h-dp(16,s)},stroke2);
            center_label(r,{vstart,b.y+dp(3,s),
                         std::max(15,b.x+b.w-vstart),b.h-dp(6,s)},
                         original.c_str(),std::max(11,body_px),ink2,false);
            label(r,vstart+dp(8,s),b.y+(b.h-body_px)/2,"<",
                  body_px,gold,true);
            label(r,b.x+b.w-dp(22,s),b.y+(b.h-body_px)/2,">",
                  body_px,gold,true);
        }else{
            const char* name=item.value==8?"Continuar jogo":"Sair do jogo";
            const char* detail=item.value==8?"Voltar para aventura":"Confirmar antes de sair";
            label(r,b.x+dp(17,s),b.y+dp(11,s),name,body_px,ink2,true,b.w-dp(40,s));
            label(r,b.x+dp(17,s),b.y+dp(38,s),detail,small_px,lilac,false,b.w-dp(40,s));
        }
    }
    if(dusk_modern::state.tab==2){
        const int x=v.content.x+dp(15,s),y=v.content.y+dp(14,s);
        label(r,x,y,"JOGUE DO SEU JEITO",dp(20,s),ink2,true,
              v.content.w-dp(30,s));
        const char* names[]={"Teclado","Controle","Mouse","Touch"};
        const char* details[]={"Setas / Enter / Esc","Direcional / A / B / Select",
                              "Clique / Roda / Arraste","Toque / Deslize / Arraste"};
        const int spacing=dp(74,s),first=y+dp(49,s);
        for(int i=0;i<4;i++){
            Rect b{x,first+i*spacing,v.content.w-dp(28,s),dp(64,s)};
            bevel(r,b,dp(8,s),tile,stroke2);
            label(r,b.x+dp(17,s),b.y+dp(7,s),names[i],body_px,ink2,true,b.w-dp(34,s));
            label(r,b.x+dp(17,s),b.y+dp(35,s),details[i],
                  small_px,lilac,false,b.w-dp(34,s));
        }
    }
    SDL_SetRenderClipRect(r,nullptr);
    const int scrollMax=dusk_modern::max_scroll(v);
    if(scrollMax>0){
        const int track=v.content.h-dp(12,s);
        const int thumb=std::max(dp(30,s),
                 track*v.content.h/std::max(1,v.content_height));
        const int pos=dusk_modern::state.scroll*(track-thumb)/scrollMax;
        rect(r,{v.content.x+v.content.w-dp(3,s),v.content.y+dp(6,s)+pos,
                dp(3,s),thumb},bright);
    }
    const Rect foot{v.panel.x+dp(6,s),v.footer.y-dp(1,s),
                    v.panel.w-dp(12,s),v.footer.h+dp(2,s)};
    bevel(r,foot,dp(9,s),{32,21,89},{83,61,158});
    const int ky=foot.y+dp(17,s);
    octagon(r,{foot.x+dp(19,s),foot.y+dp(13,s),dp(27,s),dp(27,s)},dp(6,s),{165,152,228});
    center_label(r,{foot.x+dp(19,s),foot.y+dp(13,s),dp(27,s),dp(27,s)},
                 "B",small_px,bg,true);
    label(r,foot.x+dp(54,s),ky,"Voltar",body_px,ink2);
    const int second=foot.x+dp(142,s);
    octagon(r,{second,foot.y+dp(13,s),dp(27,s),dp(27,s)},dp(6,s),{165,152,228});
    center_label(r,{second,foot.y+dp(13,s),dp(27,s),dp(27,s)},
                 "A",small_px,bg,true);
    label(r,second+dp(35,s),ky,"Selecionar",body_px,ink2);
    if(foot.w>dp(670,s))label(r,foot.x+foot.w-dp(140,s),ky,
                                 "Navegar",body_px,lilac);
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