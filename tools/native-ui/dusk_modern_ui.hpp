#pragma once
// Dusk host UI. Only SDL presentation/input; never touches emulated ARM or save contents.
// Included AFTER the legacy Dusk helpers in frontend.cpp so settings/presentation
// remain the single source of truth.
#include <array>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <string>

namespace dusk_modern {
using Rect = dusk_native::Rect;
struct Item { Rect rect{}; int kind=0; int value=0; };
struct View {
    Rect panel{}, title{}, tabs[4]{}, content{}, close{}, footer{};
    std::array<Item, 16> items{};
    int count=0;
    int content_height=0;
};
struct State {
    int tab=0;
    int focus=0;
    int scroll=0;
    bool touch=false;
    bool finger_active=false;
    bool finger_moved=false;
    float finger_down_y=0.f;
    int finger_start_scroll=0;
    int pending_item=-1;
    bool pip_drag=false;
    float pip_drag_x=0.f,pip_drag_y=0.f;
    float pip_origin_x=0.f,pip_origin_y=0.f;
};
inline State state{};

inline bool contains(Rect r, float x, float y) {
    return r.w>0 && r.h>0 && x>=r.x && y>=r.y &&
           x<r.x+r.w && y<r.y+r.h;
}
inline void fill(SDL_Renderer* r, Rect b, uint8_t cr,uint8_t cg,uint8_t cb,uint8_t a=255) {
    if(b.w>0 && b.h>0) dusk_fill(r,b,cr,cg,cb,a);
}
inline void stroke(SDL_Renderer* r, Rect b, uint8_t red,uint8_t green,uint8_t blue) {
    if(b.w>0 && b.h>0) dusk_outline(r,b,red,green,blue);
}
inline void text(SDL_Renderer* r,int x,int y,const char* words,float scale=1.5f) {
    dusk_text(r,x,y,words,scale);
}
inline const char* mode_name(int value) {
    static constexpr const char* names[6] = {
        "MODERN", "FLOATING", "CLASSIC", "SIDE BY SIDE", "MAIN ONLY", "FOCUS + PIP"
    };
    return value>=0 && value<6?names[value]:"";
}
inline const char* tab_name(int index) {
    static constexpr const char* tabs[4]={"SCREENS", "VIDEO", "CONTROLS", "SYSTEM"};
    return index>=0 && index<4?tabs[index]:"";
}
inline void append(View& v, Rect r, int kind, int value) {
    if (v.count<int(v.items.size())) v.items[v.count++]={r,kind,value};
}
inline View calculate(const dusk_native::Geometry& g, const FrontendPresentation& p) {
    View out{};
    const int w=std::max(1,g.play.w), h=std::max(1,g.play.h);
    const bool narrow=w<730 || w<h;
    const int pad=narrow?12:22;
    const int pw=std::max(1,std::min(w-2*pad,narrow?600:980));
    const int ph=std::max(1,std::min(h-2*pad,narrow?h-24:750));
    out.panel={(w-pw)/2,(h-ph)/2,pw,ph};
    const Rect panel=out.panel;
    out.title={panel.x+18,panel.y+12,panel.w-36,58};
    const int tab_y=panel.y+74;
    const int tab_margin=16;
    const int tab_gap=5;
    const int tw=(panel.w-tab_margin*2-tab_gap*3)/4;
    for(int i=0;i<4;i++)
        out.tabs[i]={panel.x+tab_margin+i*(tw+tab_gap),tab_y,tw,42};
    const int top=tab_y+53;
    const int footer_h=62;
    out.content={panel.x+16,top,panel.w-32,std::max(50,panel.y+panel.h-footer_h-top)};
    out.footer={panel.x+16,panel.y+panel.h-footer_h,panel.w-32,footer_h-10};
    out.close={panel.x+panel.w-70,panel.y+15,52,40};
    int y=out.content.y+8;
    const int cw=out.content.w;
    if(state.tab==0) {
        const int gap=9;
        const int columns=cw>=610?3:(cw>=380?2:1);
        const int cellw=(cw-gap*(columns-1))/columns;
        const int cellh=std::clamp(out.content.h/3,82,130);
        for(int i=0;i<6;i++) {
            const int row=i/columns, col=i%columns;
            append(out,{out.content.x+col*(cellw+gap),y+row*(cellh+gap)-state.scroll,
                        cellw,cellh},0,i);
        }
        y+=(6+columns-1)/columns*(cellh+gap)+15;
        const int itemh=std::clamp(out.content.h/7,58,78);
        for(int id : {1,2,3,7}) {
            append(out,{out.content.x,y-state.scroll,cw,itemh-7},1,id);
            y+=itemh;
        }
    } else if(state.tab==1) {
        const int itemh=std::clamp(out.content.h/5,68,90);
        for(int id:{4,5,6}) {
            append(out,{out.content.x,y-state.scroll,cw,itemh-9},1,id);
            y+=itemh;
        }
    } else if(state.tab==3) {
        int itemh=std::clamp(out.content.h/5,72,104);
        append(out,{out.content.x,y-state.scroll,cw,itemh},2,8);
        y+=itemh+12;
        append(out,{out.content.x,y-state.scroll,cw,itemh},2,9);
        y+=itemh+12;
    }
    out.content_height=std::max(0,y-out.content.y+10);
    return out;
}
inline int max_scroll(const View& v) {
    return std::max(0,v.content_height-v.content.h);
}
inline void clamp_scroll(const dusk_native::Geometry& g, const FrontendPresentation& p) {
    auto view=calculate(g,p);
    state.scroll=std::clamp(state.scroll,0,max_scroll(view));
    view=calculate(g,p);
    state.focus=std::clamp(state.focus,0,std::max(0,view.count-1));
}
inline void choose_tab(const dusk_native::Geometry& g,const FrontendPresentation& p,int tab) {
    state.tab=std::clamp(tab,0,3);
    state.focus=0;
    state.scroll=0;
    clamp_scroll(g,p);
}
inline void focus_visible(const dusk_native::Geometry& g,const FrontendPresentation& p) {
    const auto v=calculate(g,p);
    if(v.count==0)return;
    const auto rect=v.items[state.focus].rect;
    if(rect.y<v.content.y+8)state.scroll-=v.content.y+8-rect.y;
    if(rect.y+rect.h>v.content.y+v.content.h-8)
        state.scroll+=rect.y+rect.h-(v.content.y+v.content.h-8);
    clamp_scroll(g,p);
}
inline void navigate(const dusk_native::Geometry& g,const FrontendPresentation& p,int dx,int dy) {
    const auto v=calculate(g,p);
    if(v.count==0) {
        if(dx)choose_tab(g,p,(state.tab+4+(dx>0?1:-1))%4);
        return;
    }
    if(state.tab==0 && state.focus<6 && dx!=0) {
        const int col=v.content.w>=610?3:(v.content.w>=380?2:1);
        const int i=state.focus+dx;
        if(i>=0&&i<6 && i/col==state.focus/col)state.focus=i;
    } else if(dx) {
        // Value adjustment is handled by the host action.
        return;
    }
    if(dy) {
        const int next=state.focus+dy;
        state.focus=std::clamp(next,0,v.count-1);
    }
    focus_visible(g,p);
}
inline bool choose(FrontendPresentation& p,const dusk_native::Geometry& g,Item item,int direction=1) {
    if(item.kind==0) {
        p.dusk.cfg.layout=static_cast<dusk_native::Layout>(item.value);
        dusk_save(p);
        return true;
    }
    if(item.kind==1) {
        dusk_menu_action(p,item.value,direction);
        return true;
    }
    if(item.kind==2) {
        if(item.value==8) {
            p.dusk.menu_open=false;
            p.dusk.quit_confirm=false;
        } else if(item.value==9) {
            p.dusk.quit_confirm=true;
            p.dusk.quit_yes=false;
        }
        return true;
    }
    return false;
}
inline void draw_preview(SDL_Renderer* r,Rect inside,int mode,bool selected) {
    const int gap=4;
    fill(r,inside,8,12,41);
    stroke(r,inside,selected?95:55,selected?213:86,selected?255:150);
    Rect a{inside.x+gap,inside.y+gap,inside.w-2*gap,inside.h-2*gap};
    if(mode==2 || mode==3) {
        Rect one=a,two=a;
        if(mode==2){one.h=(a.h-gap)/2;two.y=one.y+one.h+gap;two.h=one.h;}
        else{one.w=(a.w-gap)/2;two.x=one.x+one.w+gap;two.w=one.w;}
        fill(r,one,50,56,145);fill(r,two,134,77,174);
    } else {
        fill(r,a,42,67,139);
        if(mode==0 || mode==1 || mode==5){
            int sw=std::max(12,a.w/3),sh=std::max(12,a.h/3);
            Rect b{a.x+a.w-sw-gap,a.y+a.h-sh-gap,sw,sh};
            if(mode==0)b.y=a.y+gap;
            if(mode==1)b.x=a.x+gap;
            fill(r,b,143,88,179);
            stroke(r,b,192,172,249);
        }
    }
}
inline void draw_panel(SDL_Renderer* r,const FrontendPresentation& p,
                       const dusk_native::Geometry& g) {
    const View v=calculate(g,p);
    fill(r,{0,0,g.play.w,g.play.h},4,7,21,218);
    fill(r,{v.panel.x+3,v.panel.y+8,v.panel.w,v.panel.h},0,4,16,140);
    fill(r,v.panel,13,17,51,251);
    stroke(r,v.panel,79,107,185);
    fill(r,{v.panel.x,v.panel.y,v.panel.w,5},72,210,255);
    text(r,v.title.x,v.title.y+3,"DIGIMON WORLD DUSK",1.25f);
    text(r,v.title.x,v.title.y+25,"SETTINGS",2.1f);
    fill(r,v.close,48,38,88);
    stroke(r,v.close,98,112,192);
    text(r,v.close.x+18,v.close.y+9,"X",1.5f);
    for(int i=0;i<4;i++) {
        Rect tab=v.tabs[i];
        const bool active=state.tab==i;
        fill(r,tab,active?72:22,active?45:28,active?147:71);
        if(active)fill(r,{tab.x,tab.y+tab.h-3,tab.w,3},91,220,255);
        const char* label=tab.w<95 ? (i==0?"DS":i==1?"VIDEO":i==2?"INPUT":"SYS") : tab_name(i);
        text(r,tab.x+std::max(6,(tab.w-int(std::string(label).size()*10))/2),
             tab.y+13,label,tab.w<95?1.05f:1.35f);
    }
    fill(r,v.content,13,20,55,220);
    // Strict clipping prevents content from painting over tabs or footer on small displays.
    const SDL_Rect clip{v.content.x,v.content.y,v.content.w,v.content.h};
    SDL_SetRenderClipRect(r,&clip);
    for(int i=0;i<v.count;i++) {
        const auto item=v.items[i];
        const Rect b=item.rect;
        if(b.y+b.h<=v.content.y || b.y>=v.content.y+v.content.h)continue;
        const bool focused=state.focus==i;
        const bool selected=item.kind==0 &&
            int(p.dusk.cfg.layout)==item.value;
        fill(r,b,selected?45:(focused?40:22),selected?51:(focused?44:31),
             selected?124:(focused?98:76),248);
        stroke(r,b,focused?108:48,focused?224:74,focused?255:132);
        if(item.kind==0) {
            draw_preview(r,{b.x+12,b.y+10,std::max(30,b.w-24),std::max(26,b.h-44)},
                         item.value,selected);
            text(r,b.x+12,b.y+b.h-25,mode_name(item.value),1.15f);
            if(selected)fill(r,{b.x+b.w-15,b.y+7,7,7},89,239,224);
        } else {
            const char* label="";
            std::string value;
            if(item.kind==1) {
                label=dusk_label(item.value);
                value=dusk_value(p,item.value);
            } else {
                label=item.value==8?"RESUME GAME":"QUIT GAME";
                value=item.value==8?"RETURN TO ADVENTURE":"CONFIRM BEFORE EXIT";
            }
            text(r,b.x+16,b.y+13,label,1.5f);
            if(b.w>470)
                text(r,b.x+16,b.y+39,value.c_str(),1.08f);
            else
                text(r,b.x+16,b.y+36,value.c_str(),1.08f);
            if(item.kind==1)
                text(r,b.x+b.w-42,b.y+b.h/2-7,">",1.45f);
        }
    }
    if(state.tab==2) {
        const int x=v.content.x+20, y=v.content.y+23;
        text(r,x,y,"ONE MENU. EVERY DEVICE.",1.6f);
        const char* desktop[]={
            "KEYBOARD   ARROWS / ENTER / ESC",
            "CONTROLLER DPAD / A / B / SELECT",
            "MOUSE      CLICK / WHEEL / DRAG",
            "TOUCH      TAP / SWIPE / DRAG",
            "DS TOUCH   USE THE LOWER SCREEN"
        };
        const char* mobile[]={
            "KEYS: ARROWS, ENTER, ESC",
            "PAD: DPAD, A, B, SELECT",
            "MOUSE: CLICK, SCROLL",
            "TOUCH: TAP, SWIPE",
            "DS TOUCH: LOWER SCREEN"
        };
        for(int i=0;i<5;i++)
            text(r,x,y+45+i*std::max(27,v.content.h/8),
                 v.content.w<530?mobile[i]:desktop[i],v.content.w<530?1.05f:1.3f);
    }
    SDL_SetRenderClipRect(r,nullptr);
    if(max_scroll(v)>0) {
        const int track=v.content.h-12;
        const int thumb=std::max(25,track*v.content.h/std::max(1,v.content_height));
        const int pos=state.scroll*(track-thumb)/std::max(1,max_scroll(v));
        fill(r,{v.content.x+v.content.w-5,v.content.y+6+pos,3,thumb},94,192,250);
    }
    fill(r,{v.footer.x,v.footer.y,v.footer.w,1},55,82,142);
    text(r,v.footer.x+6,v.footer.y+17,
         "ESC / B  BACK        ENTER / A  APPLY",1.17f);
    if(v.footer.w>660)text(r,v.footer.x+v.footer.w-210,v.footer.y+17,
                           "SELECT  SETTINGS",1.12f);
}
inline void draw_pip(SDL_Renderer* r,const FrontendPresentation& p,
                     const dusk_native::Geometry& g) {
    if(p.dusk.cfg.layout!=dusk_native::Layout::Focus)return;
    if(g.pip_restore.w>0) {
        fill(r,g.pip_restore,24,34,79,240);
        stroke(r,g.pip_restore,77,199,250);
        text(r,g.pip_restore.x+8,g.pip_restore.y+8,"SHOW SCREEN",1.12f);
        return;
    }
    if(g.pip_bar.w<=0)return;
    // Controls always visible on touch. Existing hit regions retain their semantics.
    fill(r,{g.pip_bar.x,g.pip_bar.y+5,g.pip_bar.w,g.pip_bar.h-5},
         24,22,65,239);
    fill(r,{g.pip_bar.x+6,g.pip_bar.y+3,std::max(1,g.pip_bar.w-12),2},85,214,247);
    text(r,g.pip_bar.x+10,g.pip_bar.y+9,
         p.dusk.cfg.focus_top?"LOWER / TOUCH":"UPPER SCREEN",1.12f);
    fill(r,g.pip_swap,61,48,120,242);
    fill(r,g.pip_minimize,61,48,120,242);
    text(r,g.pip_swap.x+5,g.pip_swap.y+7,"<>",1.05f);
    text(r,g.pip_minimize.x+8,g.pip_minimize.y+8,"-",1.4f);
}
inline void draw_corner(SDL_Renderer* r,const FrontendPresentation& p,
                        const dusk_native::Geometry& g) {
    // No hover-only control: smartphones cannot hover.
    fill(r,g.settings,29,28,76,235);
    stroke(r,g.settings,p.dusk.menu_open?110:69,p.dusk.menu_open?217:127,235);
    text(r,g.settings.x+11,g.settings.y+13,"PC",1.2f);
}
inline bool coordinate(FrontendPresentation& p,const SDL_Event& ev,float& x,float& y) {
    const bool finger=ev.type==SDL_EVENT_FINGER_DOWN ||
                      ev.type==SDL_EVENT_FINGER_MOTION ||
                      ev.type==SDL_EVENT_FINGER_UP;
    if(finger){
        int width=0,height=0;
        if(!SDL_GetRenderOutputSize(p.renderers[0],&width,&height) || width<1 || height<1)return false;
        x=ev.tfinger.x*width;
        y=ev.tfinger.y*height;
        state.touch=true;
        return true;
    }
    if(ev.type!=SDL_EVENT_MOUSE_BUTTON_DOWN && ev.type!=SDL_EVENT_MOUSE_BUTTON_UP &&
       ev.type!=SDL_EVENT_MOUSE_MOTION)return false;
    if(ev.type==SDL_EVENT_MOUSE_MOTION){x=ev.motion.x;y=ev.motion.y;}
    else {x=ev.button.x;y=ev.button.y;}
    return SDL_RenderCoordinatesFromWindow(p.renderers[0],x,y,&x,&y);
}
inline bool input(FrontendPresentation& p,const SDL_Event& ev) {
    if(!p.dusk.enabled || p.separate)return false;
    const auto geo=dusk_geometry(p);
    const bool finger=ev.type==SDL_EVENT_FINGER_DOWN ||
                      ev.type==SDL_EVENT_FINGER_MOTION ||
                      ev.type==SDL_EVENT_FINGER_UP;
    const bool down=ev.type==SDL_EVENT_MOUSE_BUTTON_DOWN ||
                    ev.type==SDL_EVENT_FINGER_DOWN;
    float x=0.f,y=0.f;
    const bool has_pos=coordinate(p,ev,x,y);
    if(!p.dusk.menu_open) {
        // Finger interactions on PiP chrome are host actions. Everywhere else
        // the lower-screen touch remains owned by the original NDS mapper.
        if(finger && has_pos) {
            const bool focus=p.dusk.cfg.layout==dusk_native::Layout::Focus;
            if(focus && down && contains(geo.pip_restore,x,y)) {
                p.dusk.cfg.auxiliary=true;dusk_save(p);return true;
            }
            if(focus && down && contains(geo.pip_swap,x,y)) {
                p.dusk.cfg.focus_top=!p.dusk.cfg.focus_top;
                dusk_save(p);return true;
            }
            if(focus && down && contains(geo.pip_minimize,x,y)) {
                p.dusk.cfg.auxiliary=false;dusk_save(p);return true;
            }
            if(focus && down && contains(geo.pip_bar,x,y) &&
               p.dusk.cfg.auxiliary) {
                state.pip_drag=true;
                state.pip_drag_x=x;state.pip_drag_y=y;
                const auto pip=p.dusk.cfg.focus_top?geo.bottom:geo.top;
                const float free_w=float(std::max(1,geo.play.w-pip.w-12));
                const float free_h=float(std::max(1,geo.play.h-pip.h-12));
                state.pip_origin_x=std::clamp(float(pip.x-geo.play.x)/free_w,0.f,1.f);
                state.pip_origin_y=std::clamp(float(pip.y-geo.play.y)/free_h,0.f,1.f);
                return true;
            }
            if(state.pip_drag) {
                if(ev.type==SDL_EVENT_FINGER_MOTION) {
                    const auto frame=p.dusk.cfg.focus_top?geo.bottom:geo.top;
                    const float free_x=float(std::max(1,geo.play.w-frame.w-12));
                    const float free_y=float(std::max(1,geo.play.h-frame.h-12));
                    p.dusk.cfg.floating_x=std::clamp(
                        state.pip_origin_x+(x-state.pip_drag_x)/free_x,0.f,1.f);
                    p.dusk.cfg.floating_y=std::clamp(
                        state.pip_origin_y+(y-state.pip_drag_y)/free_y,0.f,1.f);
                }
                if(ev.type==SDL_EVENT_FINGER_UP) {
                    state.pip_drag=false;
                    dusk_save(p);
                }
                return true;
            }
        }
        // Finger input is explicitly supported, without stealing gameplay taps.
        if(finger && down && has_pos && contains(geo.settings,x,y)) {
            p.dusk.menu_open=true;
            p.dusk.quit_confirm=false;
            state.focus=0;
            return true;
        }
        return false;
    }
    if(p.dusk.quit_confirm)return false; // Existing confirmed quit modal stays authoritative.
    if(has_pos) {
        if(finger) {
            const auto v=calculate(geo,p);
            if(down) {
                state.finger_active=true;
                state.finger_moved=false;
                state.finger_down_y=y;
                state.finger_start_scroll=state.scroll;
                state.pending_item=-1;
                if(contains(v.close,x,y)){p.dusk.menu_open=false;return true;}
                for(int i=0;i<4;i++) if(contains(v.tabs[i],x,y)) {
                    choose_tab(geo,p,i);return true;
                }
                if(contains(v.content,x,y))
                    for(int i=0;i<v.count;i++)
                        if(contains(v.items[i].rect,x,y)){state.pending_item=i;break;}
                return true;
            }
            if(ev.type==SDL_EVENT_FINGER_MOTION && state.finger_active) {
                if(std::abs(y-state.finger_down_y)>10.f)state.finger_moved=true;
                if(state.finger_moved){
                    state.scroll=state.finger_start_scroll+int(state.finger_down_y-y);
                    clamp_scroll(geo,p);
                }
                return true;
            }
            if(ev.type==SDL_EVENT_FINGER_UP) {
                if(state.finger_active && !state.finger_moved && state.pending_item>=0) {
                    const auto current=calculate(geo,p);
                    if(state.pending_item<current.count &&
                       contains(current.items[state.pending_item].rect,x,y)) {
                        state.focus=state.pending_item;
                        choose(p,geo,current.items[state.pending_item]);
                    }
                }
                state.finger_active=false;
                state.pending_item=-1;
                return true;
            }
        }
        if(down) {
            const auto v=calculate(geo,p);
            if(contains(v.close,x,y)) {p.dusk.menu_open=false;return true;}
            for(int i=0;i<4;i++)if(contains(v.tabs[i],x,y)) {
                choose_tab(geo,p,i);return true;
            }
            if(contains(v.content,x,y)) {
                for(int i=0;i<v.count;i++)if(contains(v.items[i].rect,x,y)) {
                    state.focus=i;
                    choose(p,geo,v.items[i]);
                    return true;
                }
            }
        }
        return true;
    }
    if(ev.type==SDL_EVENT_MOUSE_WHEEL) {
        state.scroll=std::max(0,state.scroll-int(ev.wheel.y*46));
        clamp_scroll(geo,p);
        return true;
    }
    if(ev.type==SDL_EVENT_KEY_DOWN && !ev.key.repeat) {
        switch(ev.key.scancode) {
            case SDL_SCANCODE_LEFT:
            case SDL_SCANCODE_RIGHT: {
                const int dir=ev.key.scancode==SDL_SCANCODE_RIGHT?1:-1;
                auto v=calculate(geo,p);
                if(v.count && state.tab==0 && state.focus<6){
                    navigate(geo,p,dir,0);
                } else if(v.count && v.items[state.focus].kind==1){
                    choose(p,geo,v.items[state.focus],dir);
                } else choose_tab(geo,p,(state.tab+4+dir)%4);
                return true;
            }
            case SDL_SCANCODE_UP:navigate(geo,p,0,-1);return true;
            case SDL_SCANCODE_DOWN:navigate(geo,p,0,1);return true;
            case SDL_SCANCODE_TAB:choose_tab(geo,p,(state.tab+1)%4);return true;
            case SDL_SCANCODE_PAGEUP:
                choose_tab(geo,p,(state.tab+3)%4);return true;
            case SDL_SCANCODE_PAGEDOWN:
                choose_tab(geo,p,(state.tab+1)%4);return true;
            case SDL_SCANCODE_RETURN:
            case SDL_SCANCODE_KP_ENTER:
            case SDL_SCANCODE_SPACE: {
                auto v=calculate(geo,p);
                if(v.count)choose(p,geo,v.items[state.focus]);
                return true;
            }
            // Escape/F10 use existing native menu toggle/quit modal logic.
            default:break;
        }
    }
    if(ev.type==SDL_EVENT_GAMEPAD_BUTTON_DOWN) {
        const uint8_t key=sdl_controller_button(ev);
        const auto v=calculate(geo,p);
        if(key==SDL_CONTROLLER_BUTTON_DPAD_UP){navigate(geo,p,0,-1);return true;}
        if(key==SDL_CONTROLLER_BUTTON_DPAD_DOWN){navigate(geo,p,0,1);return true;}
        if(key==SDL_CONTROLLER_BUTTON_DPAD_LEFT || key==SDL_CONTROLLER_BUTTON_DPAD_RIGHT){
            int dir=key==SDL_CONTROLLER_BUTTON_DPAD_RIGHT?1:-1;
            if(v.count && state.tab==0 && state.focus<6)navigate(geo,p,dir,0);
            else if(v.count && v.items[state.focus].kind==1)choose(p,geo,v.items[state.focus],dir);
            else choose_tab(geo,p,(state.tab+4+dir)%4);
            return true;
        }
        if(key==SDL_CONTROLLER_BUTTON_LEFTSHOULDER){
            choose_tab(geo,p,(state.tab+3)%4);return true;
        }
        if(key==SDL_CONTROLLER_BUTTON_RIGHTSHOULDER){
            choose_tab(geo,p,(state.tab+1)%4);return true;
        }
        if(key==SDL_CONTROLLER_BUTTON_A){
            if(v.count)choose(p,geo,v.items[state.focus]);
            return true;
        }
        // B/Select go through the original capture and toggling paths.
    }
    return false;
}
} // namespace dusk_modern
