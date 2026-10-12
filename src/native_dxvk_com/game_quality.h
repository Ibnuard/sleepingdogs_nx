/* SPDX-License-Identifier: MIT; reversible original-game display settings. */
#ifndef SD_GAME_QUALITY_H
#define SD_GAME_QUALITY_H
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/stat.h>
#ifdef __SWITCH__
#include <switch.h>
#endif

/* The launcher serializes these calls before starting the guest. No helper
 * edits UserOptions.dat or a save. The first original XML is never replaced.
 * Override only these system operations in the host disk-failure fixture. */
#ifndef SDGQ_WRITE
#define SDGQ_WRITE write
#endif
#ifndef SDGQ_FSYNC
#define SDGQ_FSYNC fsync
#endif
#ifndef SDGQ_RENAME
#define SDGQ_RENAME rename
#endif
#ifndef SDGQ_UNLINK
#define SDGQ_UNLINK unlink
#endif

#define SDGQ_MAX_FILE 65536u
static const char *sd_game_quality_error;
static int sdq_fail(const char *reason) {
    sd_game_quality_error=reason;
    log_line("[SD-GAME-QUALITY] FAIL %s",reason);
    return 0;
}
static int sdq_path(char out[768],const char *root,const char *suffix) {
    int n=snprintf(out,768,"%s%s",root,suffix);
    return n>=0&&n<768 ? 1 : sdq_fail("settings path is too long");
}
/* 1 regular file, 0 absent, -1 I/O error or unexpected object. */
static int sdq_exists(const char *path) {
    struct stat st;
    if(stat(path,&st)==0)return S_ISREG(st.st_mode)?1:-1;
    return errno==ENOENT?0:-1;
}
static int sdq_remove(const char *path) {
    int exists=sdq_exists(path);
    return exists==0 || (exists==1&&SDGQ_UNLINK(path)==0);
}
static int sdq_commit_parent(const char *path) {
#ifdef __SWITCH__
    (void)path;
    return R_SUCCEEDED(fsdevCommitDevice("sdmc"));
#else
    char parent[768];size_t n=strlen(path);
    if(n>=sizeof(parent))return 0;
    memcpy(parent,path,n+1);char *slash=strrchr(parent,'/');
    if(!slash)return 0;
    *slash=0;int fd=open(parent,O_RDONLY|O_DIRECTORY);
    if(fd<0)return 0;
    int ok=SDGQ_FSYNC(fd)==0;
    if(close(fd)!=0)ok=0;
    return ok;
#endif
}
static int sdq_read(const char *path,char **output,size_t *length) {
    *output=NULL;*length=0;
    int exists=sdq_exists(path);if(exists!=1)return exists;
    FILE *file=fopen(path,"rb");if(!file)return -1;
    char *data=malloc(SDGQ_MAX_FILE+1u);if(!data){fclose(file);return -1;}
    size_t n=fread(data,1,SDGQ_MAX_FILE+1u,file);
    int ok=!ferror(file)&&n<=SDGQ_MAX_FILE;
    if(fclose(file)!=0)ok=0;
    if(!ok){free(data);return -1;}
    data[n]=0;*output=data;*length=n;return 1;
}
static int sdq_write_new(const char *path,const char *data,size_t n) {
    int fd=open(path,O_CREAT|O_EXCL|O_WRONLY,0666);if(fd<0)return 0;
    size_t used=0;int ok=1;
    while(used<n){
        ssize_t wrote=SDGQ_WRITE(fd,data+used,n-used);
        if(wrote<0&&errno==EINTR)continue;
        if(wrote<=0){ok=0;break;}
        used+=(size_t)wrote;
    }
    if(ok&&SDGQ_FSYNC(fd)!=0)ok=0;
    if(close(fd)!=0)ok=0;
    return ok;
}
static int sdq_rename_absent(const char *from,const char *to) {
    return sdq_exists(to)==0&&SDGQ_RENAME(from,to)==0;
}
static int sdq_transaction_paths(const char *path,char fresh[768],char old[768],char txn[768],char done[768]) {
    return sdq_path(fresh,path,".sdq-new")&&sdq_path(old,path,".sdq-old")&&sdq_path(txn,path,".sdq-txn")&&sdq_path(done,path,".sdq-done");
}
/* 0 absent, 1 originally existed, 2 originally absent, -1 invalid. */
static int sdq_journal(const char *path) {
    char *record=NULL;size_t n=0;int found=sdq_read(path,&record,&n);
    if(found<=0)return found;
    int valid=n==8&&!memcmp(record,"SDGQ1\n",6)&&(record[6]=='E'||record[6]=='A')&&record[7]=='\n';
    int result=valid?(record[6]=='E'?1:2):-1;free(record);return result;
}
/* Pending .txn rolls back; committed .done retains the complete new target.
 * Cleanup commits old-file removal before dropping .done, so a deferred cleanup
 * cannot later silently roll back an acknowledged selection. This tests logical
 * interruption recovery, not the physical failure behavior of an SD card. */
static int sdq_recover(const char *path) {
    char fresh[768],old[768],txn[768],done[768];
    if(!sdq_transaction_paths(path,fresh,old,txn,done))return 0;
    int journal=sdq_journal(txn),committed=sdq_journal(done);
    if(journal<0||committed<0||(journal&&committed))return sdq_fail("unrecognized settings transaction; files preserved");
    int old_exists=sdq_exists(old),target_exists=sdq_exists(path);
    if(old_exists<0||target_exists<0)return sdq_fail("unexpected settings transaction object");
    if(committed){
        if(!target_exists)return sdq_fail("committed settings target is missing; files preserved");
        if(!sdq_remove(old)||!sdq_remove(fresh)||!sdq_commit_parent(path))return sdq_fail("committed settings cleanup is pending");
        if(!sdq_remove(done)||!sdq_commit_parent(path))return sdq_fail("cannot finish committed settings journal");
        return 1;
    }
    if(old_exists){
        if(!sdq_remove(path)||!sdq_rename_absent(old,path))return sdq_fail("settings rollback pending; original is retained in .sdq-old");
    }else if(journal==2){
        if(!sdq_remove(path))return sdq_fail("cannot roll back newly created settings");
    }else if(journal==1&&!target_exists){
        return sdq_fail("settings transaction is missing its original; files preserved");
    }
    if(!sdq_remove(fresh)||!sdq_remove(txn))return sdq_fail("cannot clean settings transaction");
    /* Nothing existed: permit Game settings mode even before Data exists. */
    if(!journal&&!old_exists)return 1;
    return sdq_commit_parent(path)?1:sdq_fail("cannot commit recovered settings");
}
static int sdq_atomic_write(const char *path,const char *data,size_t n) {
    char fresh[768],old[768],txn[768],done[768];
    if(!sdq_recover(path)||!sdq_transaction_paths(path,fresh,old,txn,done))return 0;
    int had=sdq_exists(path);if(had<0)return sdq_fail("settings target is not a regular file");
    char journal[8]={'S','D','G','Q','1','\n',had?'E':'A','\n'};
    if(!sdq_write_new(fresh,data,n)||!sdq_commit_parent(path)){
        sdq_remove(fresh);return sdq_fail("cannot write and flush temporary settings");
    }
    if(!sdq_write_new(txn,journal,sizeof(journal))||!sdq_commit_parent(path)){
        /* No target rename has happened. A partial journal is safe to discard. */
        sdq_remove(fresh);sdq_remove(txn);return sdq_fail("cannot commit settings transaction");
    }
    if((had&&!sdq_rename_absent(path,old))||!sdq_rename_absent(fresh,path)||!sdq_commit_parent(path)){
        sdq_recover(path);return sdq_fail("settings replacement failed; rollback attempted");
    }
    if(!sdq_rename_absent(txn,done)){
        sdq_recover(path);return sdq_fail("cannot mark settings committed; rollback attempted");
    }
    if(!sdq_commit_parent(path)){
        /* Retain the old file until the committed marker is durable. A failed
         * reverse rename leaves .done and both complete files for recovery. */
        if(sdq_rename_absent(done,txn))sdq_recover(path);
        return sdq_fail("settings commit failed; rollback attempted");
    }
    /* .done makes recovery keep the new target even if unlink fails. */
    if(!sdq_recover(path))log_line("[SD-GAME-QUALITY] committed settings retained; cleanup deferred");
    sd_game_quality_error=NULL;
    return 1;
}

static int sdq_space(char c){return c==' '||c=='\t'||c=='\r'||c=='\n';}
static int sdq_skip(const char **cursor) {
    const char *p=*cursor;
    for(;;){
        while(sdq_space(*p))++p;
        if(strncmp(p,"<!--",4))break;
        const char *end=strstr(p+4,"-->");if(!end)return 0;
        const char *dash=strstr(p+4,"--");if(dash!=end)return 0;
        p=end+3;
    }
    *cursor=p;return 1;
}
static int sdq_tag(const char **cursor,const char *name,int closing) {
    const char *p=*cursor;size_t n=strlen(name);
    if(*p++!='<')return 0;
    if(closing&&*p++!='/')return 0;
    if(strncmp(p,name,n))return 0;
    p+=n;
    while(sdq_space(*p))++p;
    if(*p++!='>')return 0;
    *cursor=p;return 1;
}
static int sdq_integer(const char *start,const char *end,uint32_t *value) {
    uint64_t n=0;if(start==end)return 0;
    for(const char *p=start;p<end;++p){
        if(*p<'0'||*p>'9')return 0;
        n=n*10+(unsigned)(*p-'0');if(n>UINT32_MAX)return 0;
    }
    *value=(uint32_t)n;return 1;
}
static int sdq_field_error(const char *field,const char *start,const char *end,const char *reason) {
    static char message[128];char preview[25];size_t n=0;
    while(start<end&&n<sizeof(preview)-1){
        unsigned char c=(unsigned char)*start++;preview[n++]=c>=32&&c<127?(char)c:'?';
    }
    preview[n]=0;
    snprintf(message,sizeof(message),"%s %s: '%s'%s",reason,field,preview,start<end?"...":"");
    return sdq_fail(message);
}
/* Flat scalar schema is verified against the original game's reader/writer.
 * ScalingMode/ScanlineMode are strings and StereoEyeDistance is a float.
 * Their text is left untouched. Missing targets cannot safely be synthesized. */
static int sdq_light_xml(const char *source,size_t length,char **output,size_t *out_length) {
    static const char *fields[]={"Version","AdapterUID","MonitorUID","ResolutionWidth","ResolutionHeight",
        "RefreshRateNumerator","RefreshRateDenominator","ScalingMode","ScanlineMode","Fullscreen","Stereo3D",
        "StereoEyeDistance","VSync","AAQuality","HighResTextures","ShadowRes","ShadowFilter","MotionBlur","SSAO",
        "FPSLimiter","Option3DDepth","Option3DConvergence","WorldDensity","GlobalSetting"};
    static const char *values[]={NULL,NULL,NULL,"1280","720",NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,"0","0","0","0","0","0",NULL,NULL,NULL,"0","0"};
    struct replacement {const char *start,*end,*value;} replacements[24];unsigned edits=0;
    uint32_t seen=0;const char *p=source;*output=NULL;*out_length=0;
    if(!length||length>SDGQ_MAX_FILE||memchr(source,0,length))return sdq_fail("invalid or oversized DisplaySettings.xml");
    if(length>=3&&(unsigned char)p[0]==0xef&&(unsigned char)p[1]==0xbb&&(unsigned char)p[2]==0xbf)p+=3;
    while(sdq_space(*p))++p;
    if(!strncmp(p,"<?xml ",6)){
        static const char *declarations[]={"<?xml version=\"1.0\"?>","<?xml version=\"1.0\" encoding=\"ascii\"?>",
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>","<?xml version=\"1.0\" encoding=\"utf-8\"?>"};
        size_t matched=0;
        for(unsigned i=0;i<sizeof(declarations)/sizeof(*declarations);++i){
            size_t n=strlen(declarations[i]);if(!strncmp(p,declarations[i],n)){matched=n;break;}
        }
        if(!matched)return sdq_fail("unsupported XML declaration; file preserved");
        p+=matched;
    }
    if(!sdq_skip(&p)||!sdq_tag(&p,"DisplaySettings",0))return sdq_fail("expected a flat DisplaySettings root without attributes");
    for(;;){
        if(!sdq_skip(&p))return sdq_fail("malformed XML comment");
        if(!strncmp(p,"</DisplaySettings",17))break;
        if(*p!='<')return sdq_fail("unexpected XML structure");
        unsigned index=24;
        for(unsigned i=0;i<24;++i){const char *q=p;if(sdq_tag(&q,fields[i],0)){index=i;p=q;break;}}
        if(index==24)return sdq_fail("unknown or attributed DisplaySettings field; file preserved");
        if(seen&(1u<<index))return sdq_fail("duplicate DisplaySettings field; file preserved");
        seen|=1u<<index;
        const char *start=p,*end=strchr(p,'<');if(!end)return sdq_fail("missing XML closing tag");
        for(const char *q=start;q<end;++q)if(*q=='&'||((unsigned char)*q<32&&!sdq_space(*q)))return sdq_fail("unsupported XML field text");
        p=end;if(!sdq_tag(&p,fields[index],1))return sdq_fail("mismatched or nested XML field");
        while(start<end&&sdq_space(*start))++start;
        while(end>start&&sdq_space(end[-1]))--end;
        if(index==0||values[index]){
            /* The supplied original-game XML stores GlobalSetting=-1. Accept
             * that one sentinel, then normalize it to0 along with the Light
             * values. Keep all other negative/malformed scalars rejected. */
            int custom=index==23&&end-start==2&&start[0]=='-'&&start[1]=='1';
            uint32_t number=0;
            if(!custom&&!sdq_integer(start,end,&number))return sdq_field_error(fields[index],start,end,"Invalid numeric");
            if(index==0&&number!=1)return sdq_field_error(fields[index],start,end,"Unsupported");
            if((index==3||index==4)&&!number)return sdq_field_error(fields[index],start,end,"Invalid zero");
        }
        if(values[index])replacements[edits++]=(struct replacement){start,end,values[index]};
    }
    if(!sdq_tag(&p,"DisplaySettings",1)||!sdq_skip(&p)||*p)return sdq_fail("unexpected trailing XML structure");
    if(!(seen&1u))return sdq_fail("missing DisplaySettings Version");
    for(unsigned i=0;i<24;++i)if(values[i]&&!(seen&(1u<<i)))return sdq_fail("missing graphics fields; save Display options in the game first");
    char *result=malloc(length+256);if(!result)return sdq_fail("cannot allocate graphics settings");
    const char *copied=source;size_t used=0;
    for(unsigned i=0;i<edits;++i){
        size_t n=(size_t)(replacements[i].start-copied),v=strlen(replacements[i].value);
        memcpy(result+used,copied,n);used+=n;memcpy(result+used,replacements[i].value,v);used+=v;copied=replacements[i].end;
    }
    size_t remaining=length-(size_t)(copied-source);memcpy(result+used,copied,remaining);used+=remaining;result[used]=0;
    *output=result;*out_length=used;return 1;
}
static int sd_game_quality_load(const char *root) {
    char path[768],*data=NULL;size_t n=0;sd_game_quality_error=NULL;
    if(!sdq_path(path,root,"/launcher/game-quality.txt")||!sdq_recover(path))return 0;
    int found=sdq_read(path,&data,&n),mode=0;
    if(found==1&&n==2&&(data[0]=='0'||data[0]=='1')&&data[1]=='\n')mode=data[0]-'0';
    else if(found!=0)sdq_fail("invalid game-quality.txt; using Game settings");
    free(data);return mode;
}
static int sd_game_quality_save(const char *root,int mode) {
    char path[768],dir[768];sd_game_quality_error=NULL;
    if(mode<0||mode>1)return sdq_fail("invalid graphics mode");
    if(!sdq_path(dir,root,"/launcher")||!sdq_path(path,root,"/launcher/game-quality.txt"))return 0;
    if(mkdir(dir,0777)!=0&&errno!=EEXIST)return sdq_fail("cannot create launcher settings directory");
    char bytes[2]={(char)('0'+mode),'\n'};return sdq_atomic_write(path,bytes,sizeof(bytes));
}
static int sd_game_quality_apply(const char *root,int mode) {
    char path[768],backup[768],*original=NULL,*light=NULL;size_t n=0,light_n=0;sd_game_quality_error=NULL;
    if(mode<0||mode>1)return sdq_fail("invalid graphics mode");
    if(!sdq_path(path,root,"/drive_c/SleepingDogs/Data/DisplaySettings.xml")||
       !sdq_path(backup,path,".fextendo-original")||!sdq_recover(path))return 0;
    if(!mode){log_line("[SD-GAME-QUALITY] mode=game; current display options retained");return 1;}
    int found=sdq_read(path,&original,&n);
    if(found==0)return sdq_fail("Open game once, save Display options, then enable Light720p");
    if(found<0)return sdq_fail("cannot read DisplaySettings.xml");
    if(!sdq_light_xml(original,n,&light,&light_n)){free(original);return 0;}
    if(!sdq_recover(backup)){free(original);free(light);return 0;}
    int exists=sdq_exists(backup),ok=1;
    if(exists<0)ok=sdq_fail("original graphics backup is not a regular file");
    else if(!exists)ok=sdq_atomic_write(backup,original,n);
    else {
        char *saved=NULL,*checked=NULL;size_t saved_n=0,checked_n=0;
        if(sdq_read(backup,&saved,&saved_n)!=1)ok=sdq_fail("cannot read original graphics backup");
        else ok=sdq_light_xml(saved,saved_n,&checked,&checked_n);
        free(saved);free(checked);
    }
    if(ok&&(n!=light_n||memcmp(original,light,n)))ok=sdq_atomic_write(path,light,light_n);
    free(original);free(light);
    if(ok)log_line("[SD-GAME-QUALITY] mode=Light720p resolution=1280x720 WorldDensity=0 ShadowRes=0 ShadowFilter=0 MotionBlur=0 SSAO=0 AAQuality=0 HighResTextures=0 GlobalSetting=0; original preserved");
    return ok;
}
static int sd_game_quality_restore(const char *root) {
    char path[768],backup[768],*original=NULL,*validated=NULL;size_t n=0,validated_n=0;sd_game_quality_error=NULL;
    /* Disable enforcement first. A later restore failure must not cause the
     * next launch to reapply Light720p. UI must reload selection on failure. */
    if(!sd_game_quality_save(root,0))return 0;
    if(!sdq_path(path,root,"/drive_c/SleepingDogs/Data/DisplaySettings.xml")||
       !sdq_path(backup,path,".fextendo-original")||!sdq_recover(path)||!sdq_recover(backup))return 0;
    if(sdq_read(backup,&original,&n)!=1)return sdq_fail("no readable original DisplaySettings backup");
    if(!sdq_light_xml(original,n,&validated,&validated_n)){free(original);return 0;}
    free(validated);int ok=sdq_atomic_write(path,original,n);free(original);
    if(ok)log_line("[SD-GAME-QUALITY] restored first original DisplaySettings.xml; mode=game");
    return ok;
}
#endif
