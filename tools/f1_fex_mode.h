/* An explicit launcher mode overrides legacy INI flags without rewriting
 * unrelated settings. Guest tests retain the existing control profile. */
#ifndef F1_FEX_MODE_H
#define F1_FEX_MODE_H
static unsigned f1_select_fex_profile(int guest_tests)
{
    int fast=wine_nx_config_file_bool(RUNTIME_DIR "/fex-fast.txt",1);
    int fastest=wine_nx_config_file_bool(RUNTIME_DIR "/fex-fastest.txt",0);
    int vectors=wine_nx_config_file_bool(RUNTIME_DIR "/fex-relaxed-vectors.txt",0);
    const char *origin="configuration.ini / legacy";
    char value[24]={0};
    FILE *file=fopen(RUNTIME_DIR "/launcher/fex-mode.txt","rb");
    if(file) {
        size_t n=fread(value,1,sizeof(value)-1,file);
        int valid=!ferror(file) && feof(file) && !memchr(value,0,n);
        fclose(file);
        while(n && (value[n-1]=='\r'||value[n-1]=='\n'||value[n-1]==' '||value[n-1]=='\t')) value[--n]=0;
        if(valid && !strcmp(value,"fastest")) {fast=1;fastest=1;vectors=0;origin="launcher/fex-mode.txt: fastest";}
        else if(valid && !strcmp(value,"fast")) {fast=1;fastest=0;vectors=0;origin="launcher/fex-mode.txt: fast";}
        else if(valid && !strcmp(value,"control")) {fast=0;fastest=0;vectors=0;origin="launcher/fex-mode.txt: control";}
    }
    unsigned profile=pes13_fex_select_performance_profile(guest_tests,fast,fastest,vectors);
    log_line("[F1-FEX-MODE] source=%s profile=%u guest_tests=%u",origin,profile,guest_tests!=0);
    return profile;
}
#endif
