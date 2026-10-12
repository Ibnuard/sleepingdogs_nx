#include <cassert>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include "log.h"
#include "../util_env.h"
static int debug_enabled;
extern "C" int wine_nx_sd_diagnostics_active(void){return debug_enabled;}
namespace dxvk {
Logger Logger::s_instance("d3d11.log"); // Intentionally constructed before main/setenv.
namespace env {
std::string getEnvVar(const char *name){const char *p=getenv(name);return p?p:"";}
std::string getExeBaseName(){return "production-test";}
}}
int main(int argc,char **argv) {
    assert(argc==2);std::filesystem::path root=argv[1];
    setenv("DXVK_LOG_PATH",argv[1],1);setenv("DXVK_LOG_LEVEL","info",1);
    for(int i=0;i<1000;++i){dxvk::Logger::info("normal");dxvk::Logger::err("failure while quiet");}
    assert(std::filesystem::is_empty(root));
    debug_enabled=1;dxvk::Logger::info("explicit debug");
    auto file=root/"production-test_d3d11.log";
    assert(std::filesystem::is_regular_file(file));auto size=std::filesystem::file_size(file);
    debug_enabled=0;dxvk::Logger::err("must not append after quiet");
    assert(std::filesystem::file_size(file)==size);
    std::ifstream stream(file);std::string text((std::istreambuf_iterator<char>(stream)),{});
    assert(text.find("explicit debug")!=std::string::npos&&text.find("normal")==std::string::npos);
    puts("PASS actual DXVK Logger: static constructor, 2000 quiet calls, explicit Debug, quiet again");
}
