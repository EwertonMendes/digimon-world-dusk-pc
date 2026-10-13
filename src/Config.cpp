#include "dusk/Config.hpp"
#include <fstream>
#include <iomanip>
#include <sstream>
#include <string>
namespace dusk {
LayoutSettings loadSettings(const std::filesystem::path& p) {
    LayoutSettings s;
    std::ifstream in(p);
    std::string key, value;
    while(in >> key >> value) {
        try {
            if(key=="mode") { const int n=std::stoi(value); if(n>=0 && n<=4) s.mode=static_cast<DisplayMode>(n); }
            else if(key=="secondaryScale") s.secondaryScale=std::clamp(std::stof(value),0.25F,1.0F);
            else if(key=="secondaryOpacity") s.secondaryOpacity=std::clamp(std::stof(value),0.2F,1.0F);
            else if(key=="floatX") s.floatX=std::clamp(std::stof(value),0.0F,1.0F);
            else if(key=="floatY") s.floatY=std::clamp(std::stof(value),0.0F,1.0F);
            else if(key=="showSecondary") s.showSecondary=value=="1";
        } catch (const std::exception&) { /* Keep validated defaults for corrupted keys. */ }
    }
    return s;
}
bool saveSettings(const std::filesystem::path& path, const LayoutSettings& s) {
    try {
        std::filesystem::create_directories(path.parent_path());
        const auto temp = path.string()+".tmp";
        {
            std::ofstream out(temp,std::ios::trunc);
            if(!out) return false;
            out << std::setprecision(6)
                << "mode " << static_cast<int>(s.mode) << '\n'
                << "secondaryScale " << s.secondaryScale << '\n'
                << "secondaryOpacity " << s.secondaryOpacity << '\n'
                << "floatX " << s.floatX << '\n'
                << "floatY " << s.floatY << '\n'
                << "showSecondary " << (s.showSecondary?1:0) << '\n';
            out.flush();
            if(!out) return false;
        }
        // On Windows rename() cannot replace an existing destination; remove only the previous settings file.
        std::error_code ec;
        std::filesystem::rename(temp,path,ec);
        if(ec) {
            std::filesystem::remove(path,ec);
            ec.clear();
            std::filesystem::rename(temp,path,ec);
        }
        return !ec;
    } catch (const std::exception&) { return false; }
}
}
