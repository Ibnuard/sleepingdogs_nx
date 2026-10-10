/* Persistent LSFG settings; application-owned data, independent of DXVK presets. */
#ifndef SD_LSFG_SETTINGS_H
#define SD_LSFG_SETTINGS_H
struct sd_lsfg_settings { int enabled, performance, flow; };
static struct sd_lsfg_settings fx_lsfg={0,1,1};
static int fx_lsfg_available;
static const char *const fx_lsfg_motion[]={"12.5% - lowest cost","25% - balanced","50% - higher detail"};

static struct sd_lsfg_settings fx_lsfg_load(const char *root) {
    struct sd_lsfg_settings settings={0,1,1};
    char path[768], value[8]={0};
    snprintf(path,sizeof(path),"%s/launcher/lsfg.txt",root);
    size_t n=fx_read(path,value,sizeof(value));
    if(!n&&access(path,F_OK)){
        snprintf(path,sizeof(path),"%s/launcher/lsfg.txt.old",root);
        n=fx_read(path,value,sizeof(value));
    }
    if(n==6&&value[0]>='0'&&value[0]<='1'&&value[1]==' '&&
       value[2]>='0'&&value[2]<='1'&&value[3]==' '&&
       value[4]>='0'&&value[4]<='2'&&value[5]=='\n')
        settings=(struct sd_lsfg_settings){value[0]-'0',1,value[4]-'0'};
    return settings;
}
static int fx_lsfg_save(const char *root,struct sd_lsfg_settings settings) {
    if(settings.enabled<0||settings.enabled>1||settings.performance<0||
       settings.performance>1||settings.flow<0||settings.flow>2)return 0;
    char path[768],stage[800],backup[800];
    snprintf(path,sizeof(path),"%s/launcher/lsfg.txt",root);
    snprintf(stage,sizeof(stage),"%s.new",path);
    snprintf(backup,sizeof(backup),"%s.old",path);
    if(!fx_mkdir_parents(path))return 0;
    if(access(path,F_OK)&&!access(backup,F_OK)&&rename(backup,path))return 0;
    /* v15 exposes the validated, cheaper Performance path only. The middle
     * field remains compatible with prior development settings files. */
    const char value[6]={(char)('0'+settings.enabled),' ','1',
                        ' ',(char)('0'+settings.flow),'\n'};
    if(!fx_write(stage,value,sizeof(value))){unlink(stage);return 0;}
    if(unlink(backup)&&errno!=ENOENT){unlink(stage);return 0;}
    int existing=!access(path,F_OK);
    if(existing&&rename(path,backup)){unlink(stage);return 0;}
    if(rename(stage,path)){
        if(existing)rename(backup,path);
        unlink(stage);return 0;
    }
    unlink(backup);return 1;
}
#endif
