#include "dusk/Rom.hpp"
#include <algorithm>
#include <array>
#include <fstream>
#include <iomanip>
#include <limits>
#include <sstream>
#include <tuple>
#include <utility>
#include <stdexcept>
#include <span>

namespace dusk {
namespace {
using Bytes = std::vector<std::uint8_t>;
std::uint16_t u16(const Bytes& b, std::size_t p) { return static_cast<std::uint16_t>(b[p] | (b[p+1]<<8)); }
std::uint32_t u32(const Bytes& b, std::size_t p) {
    return static_cast<std::uint32_t>(b[p]) | (static_cast<std::uint32_t>(b[p+1])<<8) |
      (static_cast<std::uint32_t>(b[p+2])<<16) | (static_cast<std::uint32_t>(b[p+3])<<24);
}
std::string trimAscii(const Bytes& b, std::size_t start, std::size_t len) {
    std::string s;
    for(std::size_t i=start;i<start+len;i++) {
        const char c=static_cast<char>(b[i]);
        if(c==0) break;
        s.push_back(c>=32 && c<=126 ? c : '?');
    }
    while(!s.empty() && s.back()==' ') s.pop_back();
    return s;
}
std::uint16_t crc16(const Bytes& b) {
    std::uint16_t crc=0xffff;
    for(std::size_t i=0;i<0x15e;i++) {
        crc=static_cast<std::uint16_t>(crc ^ b[i]);
        for(int j=0;j<8;j++) crc=static_cast<std::uint16_t>((crc>>1) ^ ((crc&1)?0xa001:0));
    }
    return crc;
}
// Self-contained SHA-256 for portable builds, avoiding crypto-provider differences across runners.
constexpr std::array<std::uint32_t,64> k{0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
std::uint32_t rotate(std::uint32_t v, unsigned shift) {return (v>>shift)|(v<<(32U-shift));}
std::string sha256(const Bytes& bytes) {
    std::array<std::uint32_t,8> h{0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
    const std::uint64_t size=static_cast<std::uint64_t>(bytes.size());
    const std::uint64_t total=((size+9+63)/64)*64;
    std::array<std::uint8_t,64> block{};
    for(std::uint64_t off=0;off<total;off+=64) {
        for(std::uint64_t j=0;j<64;j++) {
            const std::uint64_t index=off+j;
            if(index<size) block[static_cast<std::size_t>(j)]=bytes[static_cast<std::size_t>(index)];
            else if(index==size) block[static_cast<std::size_t>(j)]=0x80;
            else if(index>=total-8) block[static_cast<std::size_t>(j)]=static_cast<std::uint8_t>((size*8)>>(8*(total-1-index)));
            else block[static_cast<std::size_t>(j)]=0;
        }
        std::array<std::uint32_t,64> w{};
        for(int i=0;i<16;i++) { const auto j=static_cast<std::size_t>(4*i);w[static_cast<std::size_t>(i)]=(std::uint32_t(block[j])<<24)|(std::uint32_t(block[j+1])<<16)|(std::uint32_t(block[j+2])<<8)|block[j+3]; }
        for(int i=16;i<64;i++) {
            const auto x=w[static_cast<std::size_t>(i-15)],y=w[static_cast<std::size_t>(i-2)];
            w[static_cast<std::size_t>(i)]=(rotate(y,17)^rotate(y,19)^(y>>10))+w[static_cast<std::size_t>(i-7)]+(rotate(x,7)^rotate(x,18)^(x>>3))+w[static_cast<std::size_t>(i-16)];
        }
        auto [a,b,c,d,e,f,g,hh]=std::tuple{h[0],h[1],h[2],h[3],h[4],h[5],h[6],h[7]};
        for(int i=0;i<64;i++) {
            const std::uint32_t s1=rotate(e,6)^rotate(e,11)^rotate(e,25);
            const std::uint32_t t1=hh+s1+((e&f)^(~e&g))+k[static_cast<std::size_t>(i)]+w[static_cast<std::size_t>(i)];
            const std::uint32_t s0=rotate(a,2)^rotate(a,13)^rotate(a,22);
            const std::uint32_t t2=s0+((a&b)^(a&c)^(b&c));
            hh=g;g=f;f=e;e=d+t1;d=c;c=b;b=a;a=t1+t2;
        }
        const std::array<std::uint32_t,8> v{a,b,c,d,e,f,g,hh};
        for(std::size_t i=0;i<8;i++) h[i]+=v[i];
    }
    std::ostringstream out;
    out<<std::hex<<std::setfill('0');
    for(const auto v:h) out<<std::setw(8)<<v;
    return out.str();
}
bool spanValid(std::uint64_t length, std::uint64_t offset, std::uint64_t size) {return offset<=length && size<=length-offset;}
std::string hex(std::uint32_t v) {std::ostringstream out;out<<"0x"<<std::hex<<v;return out.str();}
std::string escaped(const std::string& input) {
    std::string out;
    for(const auto c:input) { if(c=='"'||c=='\\') out+='\\'; if(static_cast<unsigned char>(c)<32) continue;out+=c; }
    return out;
}
std::vector<Overlay> readOverlays(const Bytes& b, std::uint32_t offset,std::uint32_t size,std::uint32_t fatOffset,std::uint32_t fileCount) {
    std::vector<Overlay> result;
    for(std::uint32_t i=0;i<size/32;i++) {
        const auto start=static_cast<std::size_t>(offset)+static_cast<std::size_t>(i)*32;
        Overlay o{u32(b,start),u32(b,start+4),u32(b,start+8),u32(b,start+12),u32(b,start+16),u32(b,start+20),u32(b,start+24),u32(b,start+28),0,0};
        if(o.fileId>=fileCount) throw std::runtime_error("Overlay FAT file ID outside range");
        const auto f=static_cast<std::size_t>(fatOffset)+static_cast<std::size_t>(o.fileId)*8;
        o.fileStart=u32(b,f);o.fileEnd=u32(b,f+4);
        if(o.fileEnd<o.fileStart || !spanValid(b.size(),o.fileStart,o.fileEnd-o.fileStart)) throw std::runtime_error("Invalid overlay file range");
        result.push_back(o);
    }
    return result;
}
void emitSegment(const Bytes& all, std::uint32_t start, std::uint32_t size,const std::filesystem::path& output) {
    std::ofstream out(output,std::ios::binary | std::ios::trunc);
    if(!out) throw std::runtime_error("Cannot open output: "+output.string());
    out.write(reinterpret_cast<const char*>(all.data()+start),static_cast<std::streamsize>(size));
    if(!out) throw std::runtime_error("Cannot write: "+output.string());
}
}
bool RomInfo::matchesReferenceDusk() const {
    return title=="DS2_USA_DUSK" && gameCode=="A6RE" &&
           sha256=="df9522e07be99c5622e0211d3a50132776784db3fb28f42fc7392f588e1ae8cb";
}
RomResult inspectRom(const std::filesystem::path& path) {
    try {
        std::ifstream in(path,std::ios::binary | std::ios::ate);
        if(!in) return {{},"Cannot open ROM"};
        const auto fileSize=in.tellg();
        if(fileSize<0x200 || fileSize>512LL*1024*1024) return {{},"Unsupported ROM size (expected at least 512 bytes, max 512 MiB)"};
        Bytes b(static_cast<std::size_t>(fileSize));
        in.seekg(0);
        if(!in.read(reinterpret_cast<char*>(b.data()),static_cast<std::streamsize>(b.size()))) return {{},"Failed reading ROM"};
        RomInfo r;
        r.title=trimAscii(b,0,12);r.gameCode=trimAscii(b,0x0c,4);r.makerCode=trimAscii(b,0x10,2);
        r.fileSize=b.size(); r.headerCrc=u16(b,0x15e);r.computedHeaderCrc=crc16(b);
        if(!r.headerCrcValid()) return {{},"Invalid Nintendo DS header CRC16"};
        if(b[0x12]>3) return {{},"Unexpected device/unit code"};
        r.arm9={u32(b,0x20),u32(b,0x24),u32(b,0x28),u32(b,0x2c)};
        r.arm7={u32(b,0x30),u32(b,0x34),u32(b,0x38),u32(b,0x3c)};
        r.fntOffset=u32(b,0x40);r.fntSize=u32(b,0x44);
        r.fatOffset=u32(b,0x48);r.fatSize=u32(b,0x4c);
        r.arm9OverlayOffset=u32(b,0x50);r.arm9OverlaySize=u32(b,0x54);
        r.arm7OverlayOffset=u32(b,0x58);r.arm7OverlaySize=u32(b,0x5c);
        r.bannerOffset=u32(b,0x68);
        for(const auto& s:{r.arm9,r.arm7}) if(s.size==0 || !spanValid(b.size(),s.romOffset,s.size)) return {{},"Invalid ARM code segment range"};
        for(const auto& p:{std::pair{r.fntOffset,r.fntSize},std::pair{r.fatOffset,r.fatSize},std::pair{r.arm9OverlayOffset,r.arm9OverlaySize},std::pair{r.arm7OverlayOffset,r.arm7OverlaySize}})
            if(!spanValid(b.size(),p.first,p.second)) return {{},"ROM metadata region outside file"};
        if(r.fatSize%8!=0 || r.arm9OverlaySize%32!=0 || r.arm7OverlaySize%32!=0) return {{},"Invalid FAT or overlay table alignment"};
        r.fileCount=r.fatSize/8;
        r.arm9Overlays=readOverlays(b,r.arm9OverlayOffset,r.arm9OverlaySize,r.fatOffset,r.fileCount);
        r.arm7Overlays=readOverlays(b,r.arm7OverlayOffset,r.arm7OverlaySize,r.fatOffset,r.fileCount);
        if(r.bannerOffset && !spanValid(b.size(),r.bannerOffset,0x840)) r.warnings.push_back("Banner extends past ROM");
        r.sha256=sha256(b);
        if(!r.matchesReferenceDusk()) r.warnings.push_back("ROM does not match verified Dusk USA reference SHA-256");
        return {std::move(r),{}};
    } catch (const std::exception& e) {return {{},e.what()};}
}
bool extractCode(const std::filesystem::path& rom,const std::filesystem::path& output,std::string& error) {
    try {
        const auto parsed=inspectRom(rom);
        if(!parsed) {error=parsed.error;return false;}
        if(output.empty()) {error="Output directory is required";return false;}
        if(std::filesystem::is_directory(output/".git")) {error="Refusing extraction into a Git root";return false;}
        std::ifstream in(rom,std::ios::binary | std::ios::ate);
        const auto size=in.tellg();
        Bytes bytes(static_cast<std::size_t>(size));
        in.seekg(0);
        if(!in.read(reinterpret_cast<char*>(bytes.data()),static_cast<std::streamsize>(bytes.size()))) throw std::runtime_error("Cannot reread ROM");
        std::filesystem::create_directories(output/"overlays");
        emitSegment(bytes,parsed.info->arm9.romOffset,parsed.info->arm9.size,output/"arm9.bin");
        emitSegment(bytes,parsed.info->arm7.romOffset,parsed.info->arm7.size,output/"arm7.bin");
        for(const auto& ov:parsed.info->arm9Overlays) emitSegment(bytes,ov.fileStart,ov.fileEnd-ov.fileStart,output/"overlays"/("arm9_"+std::to_string(ov.id)+".bin"));
        for(const auto& ov:parsed.info->arm7Overlays) emitSegment(bytes,ov.fileStart,ov.fileEnd-ov.fileStart,output/"overlays"/("arm7_"+std::to_string(ov.id)+".bin"));
        std::ofstream report(output/"rom-manifest.json");
        report<<jsonReport(*parsed.info);
        return static_cast<bool>(report);
    } catch (const std::exception& e) {error=e.what();return false;}
}
std::string jsonReport(const RomInfo& r) {
    std::ostringstream ss;
    const auto segment=[&](const CodeSegment& s) {
        ss << "{\"romOffset\":"<<s.romOffset<<",\"entry\":\""<<hex(s.entry)<<"\",\"ramAddress\":\""<<hex(s.ramAddress)<<"\",\"size\":"<<s.size<<"}";
    };
    const auto overlay=[&](const std::vector<Overlay>& group) {
        ss<<'[';
        for(std::size_t i=0;i<group.size();i++) {
            if(i) ss<<',';
            const auto& o=group[i];
            ss<<"{\"id\":"<<o.id<<",\"ramAddress\":\""<<hex(o.ramAddress)<<"\",\"ramSize\":"<<o.ramSize
              <<",\"bssSize\":"<<o.bssSize<<",\"fileId\":"<<o.fileId<<",\"fileStart\":"<<o.fileStart
              <<",\"fileEnd\":"<<o.fileEnd<<"}";
        }
        ss<<']';
    };
    ss << "{\n  \"title\":\""<<escaped(r.title)<<"\",\n  \"gameCode\":\""<<escaped(r.gameCode)
       <<"\",\n  \"makerCode\":\""<<escaped(r.makerCode)<<"\",\n  \"size\":"<<r.fileSize
       <<",\n  \"sha256\":\""<<r.sha256<<"\",\n  \"matchesReferenceDusk\":"<<(r.matchesReferenceDusk()?"true":"false")
       <<",\n  \"headerCrc16Valid\":"<<(r.headerCrcValid()?"true":"false")<<",\n  \"arm9\":";
    segment(r.arm9);ss<<",\n  \"arm7\":";segment(r.arm7);
    ss<<",\n  \"fileCount\":"<<r.fileCount<<",\n  \"arm9Overlays\":";overlay(r.arm9Overlays);
    ss<<",\n  \"arm7Overlays\":";overlay(r.arm7Overlays);
    ss<<",\n  \"warnings\":[";
    for(std::size_t i=0;i<r.warnings.size();i++) {if(i) ss<<',';ss<<'"'<<escaped(r.warnings[i])<<'"';}
    ss<<"]\n}\n";
    return ss.str();
}
}
