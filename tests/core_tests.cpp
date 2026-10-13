#include "dusk/Rom.hpp"
#include "dusk/Layout.hpp"
#include "dusk/Config.hpp"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <cstdlib>
#include <string>
#include <vector>
#include <cmath>
namespace {
int failures=0;
void check(bool value,const std::string& name) {if(!value){std::cerr<<"FAIL: "<<name<<'\n';failures++;}}
}
int main() {
    using namespace dusk;
    const std::vector<DisplayMode> modes={DisplayMode::modern,DisplayMode::floating,DisplayMode::classicHorizontal,DisplayMode::classicVertical,DisplayMode::primaryOnly};
    for(auto mode:modes) for(const auto [w,h]:{std::pair{1920,1080},std::pair{1280,720},std::pair{640,480},std::pair{420,320},std::pair{3440,1440},std::pair{200,140}}) {
        LayoutSettings s; s.mode=mode;
        auto r=computeLayout(w,h,s);
        check(r.primary.w>0&&r.primary.h>0,"primary positive");
        check(r.primary.x>=0&&r.primary.y>=0&&r.primary.x+r.primary.w<=w&&r.primary.y+r.primary.h<=h,"primary within bounds");
        check(r.primary.w*kScreenHeight==r.primary.h*kScreenWidth || std::abs(r.primary.w*kScreenHeight-r.primary.h*kScreenWidth)<=kScreenHeight+kScreenWidth,"aspect ratio approximately preserved");
        if(r.visibleSecondary) check(r.secondary.x>=0&&r.secondary.y>=0&&r.secondary.x+r.secondary.w<=w&&r.secondary.y+r.secondary.h<=h,"secondary within bounds");
        int tx=-1,ty=-1;
        check(screenToTouch(r,false,r.primary.x,r.primary.y,tx,ty)&&tx==0&&ty==0,"primary touch origin");
        check(screenToTouch(r,false,r.primary.x+r.primary.w-1,r.primary.y+r.primary.h-1,tx,ty)&&tx>=0&&tx<kScreenWidth&&ty>=0&&ty<kScreenHeight,"primary touch limits");
        check(!screenToTouch(r,false,-2,-2,tx,ty),"reject touches outside screen");
        if(!r.visibleSecondary) check(!screenToTouch(r,true,0,0,tx,ty),"hidden second screen rejects touch");
    }
    auto malformed=std::filesystem::temp_directory_path()/"dusk_invalid_test.nds";
    {std::ofstream f(malformed,std::ios::binary);f<<"Not a Nintendo DS ROM";}
    check(!inspectRom(malformed),"malformed ROM is rejected");
    std::filesystem::remove(malformed);
    const auto conf=std::filesystem::temp_directory_path()/"dusk_pc_test_config"/"settings.txt";
    LayoutSettings input;input.mode=DisplayMode::floating;input.secondaryScale=0.75F;input.floatX=0.33F;input.showSecondary=false;
    check(saveSettings(conf,input),"settings save");
    const auto loaded=loadSettings(conf);
    check(loaded.mode==input.mode&&std::abs(loaded.secondaryScale-0.75F)<0.001F&&!loaded.showSecondary,"settings roundtrip");
    {std::ofstream o(conf);o<<"mode 100\nsecondaryScale -4\nfloatX bad\n";}
    const auto invalid=loadSettings(conf);
    check(invalid.mode==DisplayMode::modern&&invalid.secondaryScale>=0.25F,"settings sanitize corrupt input");
    std::filesystem::remove_all(conf.parent_path());
    if(const auto* rom=std::getenv("DUSK_TEST_ROM")) {
        auto result=inspectRom(rom);
        check(static_cast<bool>(result),"provided ROM parses");
        if(result) {
            check(result.info->matchesReferenceDusk(),"reference ROM matches exact sha256");
            check(result.info->headerCrcValid(),"reference ROM CRC16 matches");
            check(result.info->arm9Overlays.size()==18,"18 overlays ARM9");
            check(result.info->arm7Overlays.empty(),"0 overlays ARM7");
            check(result.info->fileCount==8868,"FAT file count 8868");
        }
    }
    if(failures) {std::cerr<<failures<<" failures\n";return 1;}
    std::cout<<"All tests passed\n";
    return 0;
}
