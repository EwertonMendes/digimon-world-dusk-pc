// Windows presentation prototype. Not a Nintendo DS emulator or a runnable Dusk port.
#include "dusk/Config.hpp"
#include "dusk/Layout.hpp"
#include "dusk/Rom.hpp"
#include <windows.h>
#include <windowsx.h>
#include <shellapi.h>
#include <array>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <string>
#include <vector>
#include <exception>

namespace {
constexpr wchar_t kClassName[]=L"DuskPcWindow";
struct App {
    HWND window{};
    dusk::LayoutSettings settings{};
    dusk::ScreenLayout layout{};
    std::filesystem::path configPath;
    bool fullscreen{false};
    DWORD normalStyle{};
    WINDOWPLACEMENT placement{sizeof(WINDOWPLACEMENT)};
    bool dragging{false};
    int dragOffsetX{};
    int dragOffsetY{};
    int touchX{-1};
    int touchY{-1};
    bool romLoaded{false};
    std::string romCode;
};
App g;
std::array<std::uint32_t,dusk::kScreenWidth*dusk::kScreenHeight> pixelsMain{};
std::array<std::uint32_t,dusk::kScreenWidth*dusk::kScreenHeight> pixelsAux{};

std::filesystem::path settingsPath() {
    std::filesystem::path home;
    const auto needed=GetEnvironmentVariableW(L"APPDATA",nullptr,0);
    if(needed>1) {
        std::wstring buffer(static_cast<std::size_t>(needed),L'\0');
        const auto length=GetEnvironmentVariableW(L"APPDATA",buffer.data(),needed);
        if(length>0 && length<needed) home=std::filesystem::path(buffer.substr(0,length));
    }
    if(home.empty()) home=std::filesystem::temp_directory_path();
    return home/L"DuskPC"/L"presentation-settings.txt";
}

void syntheticFrames() {
    for(int y=0;y<dusk::kScreenHeight;y++) for(int x=0;x<dusk::kScreenWidth;x++) {
        const auto n=static_cast<std::size_t>(y*dusk::kScreenWidth+x);
        const auto v=static_cast<std::uint32_t>(18+(x*25)/dusk::kScreenWidth);
        pixelsMain[n]=0xff000000u | (v<<16) | ((v+20)<<8) | (v+46);
        if(x%32==0 || y%32==0) pixelsMain[n]=0xff3d476au;
        const auto a=static_cast<std::uint32_t>(35+(y*25)/dusk::kScreenHeight);
        pixelsAux[n]=0xff000000u|((a+27)<<16)|(a<<8)|(a+33);
        if(x%32==0||y%32==0) pixelsAux[n]=0xff61577du;
    }
}
void writeText(HDC dc, const std::wstring& message,int x,int y,int w,int h,COLORREF color,int point=20,bool center=false) {
    const int logical= -MulDiv(point,GetDeviceCaps(dc,LOGPIXELSY),72);
    HFONT font=CreateFontW(logical,0,0,0,FW_SEMIBOLD,FALSE,FALSE,FALSE,DEFAULT_CHARSET,
                           OUT_DEFAULT_PRECIS,CLIP_DEFAULT_PRECIS,CLEARTYPE_QUALITY,DEFAULT_PITCH,L"Segoe UI");
    auto old=SelectObject(dc,font);
    SetTextColor(dc,color);SetBkMode(dc,TRANSPARENT);
    RECT rect{x,y,x+w,y+h};
    DrawTextW(dc,message.c_str(),-1,&rect,(center?DT_CENTER:DT_LEFT)|DT_VCENTER|DT_SINGLELINE|DT_END_ELLIPSIS);
    SelectObject(dc,old);DeleteObject(font);
}
void drawSurface(HDC dc,const dusk::Rect& r,const std::uint32_t* pixels,const std::wstring& title,COLORREF border) {
    if(r.w<1||r.h<1) return;
    RECT frame{r.x-2,r.y-2,r.x+r.w+2,r.y+r.h+2};
    HBRUSH brush=CreateSolidBrush(border);
    FrameRect(dc,&frame,brush);DeleteObject(brush);
    BITMAPINFO bmp{};
    bmp.bmiHeader.biSize=sizeof(BITMAPINFOHEADER);
    bmp.bmiHeader.biWidth=dusk::kScreenWidth;
    bmp.bmiHeader.biHeight=-dusk::kScreenHeight;
    bmp.bmiHeader.biPlanes=1;
    bmp.bmiHeader.biBitCount=32;
    bmp.bmiHeader.biCompression=BI_RGB;
    SetStretchBltMode(dc,COLORONCOLOR);
    StretchDIBits(dc,r.x,r.y,r.w,r.h,0,0,dusk::kScreenWidth,dusk::kScreenHeight,
                  pixels,&bmp,DIB_RGB_COLORS,SRCCOPY);
    writeText(dc,title,r.x+6,r.y+8,std::max(1,r.w-12),24,RGB(239,239,255),14);
}
void toggleFullScreen() {
    if(!g.window) return;
    if(!g.fullscreen) {
        g.normalStyle=static_cast<DWORD>(GetWindowLongPtrW(g.window,GWL_STYLE));
        g.placement.length=sizeof(WINDOWPLACEMENT);
        GetWindowPlacement(g.window,&g.placement);
        MONITORINFO monitor{sizeof(MONITORINFO)};
        if(!GetMonitorInfoW(MonitorFromWindow(g.window,MONITOR_DEFAULTTONEAREST),&monitor)) return;
        SetWindowLongPtrW(g.window,GWL_STYLE,static_cast<LONG_PTR>(g.normalStyle & ~WS_OVERLAPPEDWINDOW));
        SetWindowPos(g.window,HWND_TOP,monitor.rcMonitor.left,monitor.rcMonitor.top,
                     monitor.rcMonitor.right-monitor.rcMonitor.left,monitor.rcMonitor.bottom-monitor.rcMonitor.top,
                     SWP_FRAMECHANGED|SWP_NOOWNERZORDER);
        g.fullscreen=true;
    } else {
        SetWindowLongPtrW(g.window,GWL_STYLE,static_cast<LONG_PTR>(g.normalStyle));
        SetWindowPlacement(g.window,&g.placement);
        SetWindowPos(g.window,nullptr,0,0,0,0,SWP_NOMOVE|SWP_NOSIZE|SWP_NOZORDER|SWP_FRAMECHANGED);
        g.fullscreen=false;
    }
}
void update() { if(g.window) InvalidateRect(g.window,nullptr,FALSE); }
LRESULT CALLBACK windowProc(HWND window,UINT msg,WPARAM wp,LPARAM lp) {
    switch(msg) {
    case WM_ERASEBKGND: return 1;
    case WM_GETMINMAXINFO: {
        auto* info=reinterpret_cast<MINMAXINFO*>(lp);
        info->ptMinTrackSize={420,320};return 0;
    }
    case WM_SIZE: update();return 0;
    case WM_KEYDOWN: {
        if(wp==VK_F11 || (wp==VK_RETURN && (GetKeyState(VK_MENU)&0x8000))) toggleFullScreen();
        else if(wp==VK_ESCAPE && g.fullscreen) toggleFullScreen();
        else if(wp==VK_F2) g.settings.showSecondary=!g.settings.showSecondary;
        else if(wp==VK_F3) g.settings.mode=static_cast<dusk::DisplayMode>((static_cast<int>(g.settings.mode)+1)%5);
        else if(wp==VK_ADD || wp==VK_OEM_PLUS) g.settings.secondaryScale=std::min(1.0F,g.settings.secondaryScale+0.05F);
        else if(wp==VK_SUBTRACT || wp==VK_OEM_MINUS) g.settings.secondaryScale=std::max(0.25F,g.settings.secondaryScale-0.05F);
        else if(wp==VK_F1) MessageBoxW(window,L"F2: show/hide auxiliary screen\nF3: change screen layout\nF11: fullscreen\n+/-: floating screen size\nDrag auxiliary screen in Floating mode\n\nThis is a presentation prototype ONLY. It does not execute the DS ROM.",L"Dusk PC - Controls",MB_OK|MB_ICONINFORMATION);
        update();return 0;
    }
    case WM_LBUTTONDOWN: {
        const int x=GET_X_LPARAM(lp),y=GET_Y_LPARAM(lp);
        if(g.settings.mode==dusk::DisplayMode::floating && g.layout.visibleSecondary && g.layout.secondary.contains(x,y)) {
            g.dragging=true;g.dragOffsetX=x-g.layout.secondary.x;g.dragOffsetY=y-g.layout.secondary.y;
            SetCapture(window);
        }
        // Touch mapping is validated in core tests. No game is listening yet.
        if(!g.dragging) (void)dusk::screenToTouch(g.layout,true,x,y,g.touchX,g.touchY);
        update();return 0;
    }
    case WM_MOUSEMOVE: {
        if(g.dragging) {
            RECT rc{};GetClientRect(window,&rc);
            const int w=std::max(1,static_cast<int>(rc.right-rc.left)),h=std::max(1,static_cast<int>(rc.bottom-rc.top));
            const int px=GET_X_LPARAM(lp)-g.dragOffsetX;
            const int py=GET_Y_LPARAM(lp)-g.dragOffsetY;
            g.settings.floatX=static_cast<float>(std::clamp(px,0,std::max(0,w-g.layout.secondary.w)))/std::max(1,w-g.layout.secondary.w);
            g.settings.floatY=static_cast<float>(std::clamp(py,0,std::max(0,h-g.layout.secondary.h)))/std::max(1,h-g.layout.secondary.h);
            update();
        }
        return 0;
    }
    case WM_LBUTTONUP: if(g.dragging){g.dragging=false;ReleaseCapture();}return 0;
    case WM_PAINT: {
        PAINTSTRUCT ps{};auto dc=BeginPaint(window,&ps);
        RECT client{};GetClientRect(window,&client);
        HBRUSH background=CreateSolidBrush(RGB(15,18,31));FillRect(dc,&client,background);DeleteObject(background);
        const int w=std::max(0,static_cast<int>(client.right-client.left)),h=std::max(0,static_cast<int>(client.bottom-client.top));
        const int contentHeight=std::max(0,h-96);
        g.layout=dusk::computeLayout(w,contentHeight,g.settings);
        drawSurface(dc,g.layout.primary,pixelsMain.data(),L"PRIMARY - SYNTHETIC FRAME",RGB(98,103,182));
        if(g.layout.visibleSecondary) drawSurface(dc,g.layout.secondary,pixelsAux.data(),L"AUXILIARY - TEST FRAME",RGB(152,113,179));
        HBRUSH bottom=CreateSolidBrush(RGB(26,31,49));
        RECT band{0,contentHeight,w,h};FillRect(dc,&band,bottom);DeleteObject(bottom);
        writeText(dc,L"DUSK RECOMPILED  /  PRESENTATION TEST",18,contentHeight+8,std::max(1,w-36),27,RGB(237,229,255),17);
        std::wstring status=L"No native game execution  |  F1 Help  F2 Show/hide  F3 Layout  F11 Fullscreen  +/- Resize";
        writeText(dc,status,18,contentHeight+36,std::max(1,w-36),20,RGB(183,194,219),11);
        std::wstring mode=L"Layout: "+std::wstring(dusk::modeName(g.settings.mode),dusk::modeName(g.settings.mode)+std::char_traits<char>::length(dusk::modeName(g.settings.mode)));
        if(g.romLoaded) mode+=L"  |  Dusk USA ROM identified (NOT executing)";
        if(g.touchX>=0) mode+=L"  |  Last touch: "+std::to_wstring(g.touchX)+L","+std::to_wstring(g.touchY);
        writeText(dc,mode,18,contentHeight+61,std::max(1,w-36),22,RGB(164,173,202),11);
        EndPaint(window,&ps);return 0;
    }
    case WM_DESTROY:
        (void)dusk::saveSettings(g.configPath,g.settings);
        PostQuitMessage(0);return 0;
    default: return DefWindowProcW(window,msg,wp,lp);
    }
}
}
int WINAPI wWinMain(HINSTANCE instance,HINSTANCE, PWSTR,int show) {
    try {
        g.configPath=settingsPath();g.settings=dusk::loadSettings(g.configPath);
        int argc=0;
        auto argv=CommandLineToArgvW(GetCommandLineW(),&argc);
        if(argv) {
            if(argc>1) {
                const auto info=dusk::inspectRom(argv[1]);
                if(info) {g.romLoaded=info.info->matchesReferenceDusk();g.romCode=info.info->gameCode;}
                else MessageBoxW(nullptr,L"Could not validate ROM argument. Check file path and ROM integrity.",L"ROM validation",MB_ICONWARNING|MB_OK);
            }
            LocalFree(argv);
        }
        syntheticFrames();
        WNDCLASSEXW wc{sizeof(wc)};
        wc.style=CS_HREDRAW|CS_VREDRAW;
        wc.lpfnWndProc=windowProc;wc.hInstance=instance;
        wc.hCursor=LoadCursorW(nullptr,IDC_ARROW);
        wc.lpszClassName=kClassName;
        if(!RegisterClassExW(&wc)) return 1;
        g.window=CreateWindowExW(0,kClassName,L"Digimon World Dusk Recompiled | v0.29 - Presentation Prototype (NOT GAME)",
            WS_OVERLAPPEDWINDOW|WS_VISIBLE,CW_USEDEFAULT,CW_USEDEFAULT,1280,800,nullptr,nullptr,instance,nullptr);
        if(!g.window) return 1;
        ShowWindow(g.window,show);UpdateWindow(g.window);
        MSG msg{};
        while(GetMessageW(&msg,nullptr,0,0)>0) {TranslateMessage(&msg);DispatchMessageW(&msg);}
        return static_cast<int>(msg.wParam);
    } catch (const std::exception&) {
        MessageBoxW(nullptr,L"Dusk PC failed initializing. See environment and file permissions.",L"Error",MB_OK|MB_ICONERROR);
        return 1;
    }
}
