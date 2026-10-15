#include "dusk_localization.hpp"
#include <cassert>
#include <filesystem>
#include <fstream>
#include <string>
int main() {
    using namespace dusk_localization;
    static_assert(kCodes.size()==4);
    assert(parse("pt-BR")==Language::portuguese);
    assert(parse("es-ES")==Language::spanish);
    assert(parse("unknown")==Language::english);
    assert(next(Language::english,-1)==Language::japanese);
    assert(next(Language::japanese,1)==Language::english);
    assert(std::string(ui("language",Language::spanish))=="Idioma");
    TranslationCatalog catalog;
    const std::string origin="Hello [PLAYER_NAME] [RED_TEXT]Digimon[RED_TEXT]!";
    assert(catalog.resolve("msgpak/0001",1,Language::portuguese,origin)==origin);
    const std::string pt="Ola [PLAYER_NAME]! Este texto pode ser muito mais comprido "
                         "do que a mensagem original e manter [RED_TEXT]Digimon[RED_TEXT].";
    assert(pt.size()>origin.size());
    assert(catalog.set("msgpak/0001",1,Language::portuguese,pt));
    assert(catalog.resolve("msgpak/0001",1,Language::portuguese,origin)==pt);
    assert(catalog.resolve("msgpak/0001",1,Language::english,origin)==origin);
    assert(catalog.resolve("msgpak/0001",2,Language::portuguese,origin)==origin);
    assert(catalog.resolve("arm9",1,Language::portuguese,origin)==origin);
    // A missing control marker is rejected rather than breaking guest dialogue.
    assert(catalog.set("msgpak/0001",1,Language::spanish,"Hola Digimon"));
    assert(catalog.resolve("msgpak/0001",1,Language::spanish,origin)==origin);
    assert(!catalog.set("",1,Language::portuguese,"missing region"));
    assert(!catalog.set("msgpak",1,Language::english,"not allowed"));
    assert(!catalog.set("msgpak",1,Language::spanish,std::string(1,static_cast<char>(0xC3))));
    assert(catalog.size()==1);
    // User preferences are outside game EEPROM. A corrupt locale falls back to English.
    auto directory=std::filesystem::temp_directory_path()/"dusk-localization-smoke";
    std::filesystem::create_directories(directory);
    preference_loaded=false;
    load_preference(directory/"native-layout-v4.cfg");
    assert(active_language==Language::english);
    assert(select(Language::spanish));
    preference_loaded=false;
    load_preference(directory/"native-layout-v4.cfg");
    assert(active_language==Language::spanish);
    { std::ofstream out(preference_path,std::ios::trunc);out<<"bad-code\\n"; }
    preference_loaded=false;
    load_preference(directory/"native-layout-v4.cfg");
    assert(active_language==Language::english);
    std::filesystem::remove_all(directory);
    return 0;
}
