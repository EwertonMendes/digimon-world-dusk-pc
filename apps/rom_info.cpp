#include "dusk/Rom.hpp"
#include <iostream>
#include <string>
int main(int argc,char** argv) {
    if(argc<2) {
        std::cerr<<"Usage: dusk_rom_info <path-to-your.nds> [--json | --extract-code <private-directory>]\n";
        return 2;
    }
    const auto info=dusk::inspectRom(argv[1]);
    if(!info) { std::cerr<<"ROM validation failed: "<<info.error<<'\n';return 1; }
    const auto& r=*info.info;
    if(argc>=3 && std::string(argv[2])=="--extract-code") {
        if(argc<4) {std::cerr<<"Specify a private output directory\n";return 2;}
        std::string error;
        if(!dusk::extractCode(argv[1],argv[3],error)) {std::cerr<<"Extraction failed: "<<error<<'\n';return 1;}
        std::cout<<"Extracted private game-derived code into "<<argv[3]<<". Do not commit or share these files.\n";
        return 0;
    }
    if(argc>=3 && std::string(argv[2])!="--json") {std::cerr<<"Unknown argument\n";return 2;}
    std::cout<<dusk::jsonReport(r);
    return 0;
}
