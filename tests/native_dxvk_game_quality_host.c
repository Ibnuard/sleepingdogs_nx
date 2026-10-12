/* SPDX-License-Identifier: MIT; real filesystem XML and recovery fixture. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdarg.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/stat.h>
#include <sys/wait.h>

static unsigned checks,write_failures,rename_failures,flush_failures,unlink_failures,power_cases;
static unsigned disk_step,fail_step,crash_step;
static int failure_kind,failure_fired;
static void check(int ok,const char *text,int line){++checks;if(!ok){fprintf(stderr,"FAIL %d: %s\n",line,text);exit(1);}}
#define CHECK(x) check(!!(x),#x,__LINE__)
static void log_line(const char *format,...){(void)format;}
static int inject(int kind){
    if(!failure_kind||failure_kind==kind){
        ++disk_step;
        if(fail_step&&disk_step==fail_step){failure_fired=1;errno=EIO;return 1;}
    }
    return 0;
}
static ssize_t disk_write(int fd,const void *data,size_t n){
    if(inject(1)){++write_failures;return -1;}
    return write(fd,data,n);
}
static int disk_fsync(int fd){if(inject(2)){++flush_failures;return -1;}return fsync(fd);}
static int disk_unlink(const char *path){if(inject(4)){++unlink_failures;return -1;}return unlink(path);}
static int disk_rename(const char *from,const char *to){
    if(inject(3)){++rename_failures;return -1;}
    struct stat st;if(stat(to,&st)==0){errno=EEXIST;return -1;}
    int rc=rename(from,to);
    if(!rc&&crash_step&&++disk_step==crash_step)_exit(77);
    return rc;
}
#define SDGQ_WRITE disk_write
#define SDGQ_FSYNC disk_fsync
#define SDGQ_RENAME disk_rename
#define SDGQ_UNLINK disk_unlink
#include "game_quality.h"

static const char original_xml[]=
    "<?xml version=\"1.0\" encoding=\"ascii\"?>\r\n<!-- keep display selection -->\r\n<DisplaySettings>\r\n"
    " <Version>1</Version>\r\n <AdapterUID>-2147483647</AdapterUID>\r\n <MonitorUID>72</MonitorUID>\r\n"
    " <ResolutionWidth>1920</ResolutionWidth>\r\n <ResolutionHeight>1080</ResolutionHeight>\r\n"
    " <RefreshRateNumerator>60000</RefreshRateNumerator>\r\n <RefreshRateDenominator>1001</RefreshRateDenominator>\r\n"
    " <ScalingMode>Unspecified</ScalingMode>\r\n <ScanlineMode>Progressive</ScanlineMode>\r\n"
    " <Fullscreen>1</Fullscreen>\r\n <Stereo3D>0</Stereo3D>\r\n <StereoEyeDistance>0.012500</StereoEyeDistance>\r\n"
    " <VSync>1</VSync>\r\n <AAQuality> 2 </AAQuality>\r\n <HighResTextures>1</HighResTextures>\r\n"
    " <ShadowRes>3</ShadowRes>\r\n <ShadowFilter>2</ShadowFilter>\r\n <MotionBlur>1</MotionBlur>\r\n <SSAO>2</SSAO>\r\n"
    " <FPSLimiter>0</FPSLimiter>\r\n <Option3DDepth>7</Option3DDepth>\r\n <Option3DConvergence>8</Option3DConvergence>\r\n"
    " <WorldDensity>2</WorldDensity>\r\n <GlobalSetting>4</GlobalSetting>\r\n</DisplaySettings>\r\n";
static char root[768],target[768],backup[768],modefile[768],sentinel[768];
static void path(char out[768],const char *suffix){CHECK(sdq_path(out,root,suffix));}
static void put(const char *file,const char *text){FILE *f=fopen(file,"wb");CHECK(f!=NULL);size_t n=strlen(text);CHECK(fwrite(text,1,n,f)==n);CHECK(!fclose(f));}
static char *get(const char *file){char *data;size_t n;CHECK(sdq_read(file,&data,&n)==1);return data;}
static void same(const char *file,const char *expected){char *data=get(file);CHECK(!strcmp(data,expected));free(data);}
static void remove_artifacts(const char *file){
    char temp[768];CHECK(sdq_remove(file));
    for(unsigned i=0;i<4;++i){const char *suffix[]={".sdq-new",".sdq-old",".sdq-txn",".sdq-done"};CHECK(sdq_path(temp,file,suffix[i]));CHECK(sdq_remove(temp));}
}
static void reset(void){
    failure_kind=0;failure_fired=0;fail_step=crash_step=disk_step=0;
    remove_artifacts(target);remove_artifacts(backup);remove_artifacts(modefile);
    put(target,original_xml);put(sentinel,"save-and-UserOptions-unchanged\n");
    sd_game_quality_error=NULL;
}
static void valid_light(const char *file){
    char *text=get(file);
    CHECK(strstr(text,"<ResolutionWidth>1280</ResolutionWidth>"));
    CHECK(strstr(text,"<ResolutionHeight>720</ResolutionHeight>"));
    CHECK(strstr(text,"<AAQuality> 0 </AAQuality>"));
    CHECK(strstr(text,"<HighResTextures>0</HighResTextures>"));
    CHECK(strstr(text,"<WorldDensity>0</WorldDensity>"));
    CHECK(strstr(text,"<GlobalSetting>0</GlobalSetting>"));
    const char *untouched[]={"<?xml version=\"1.0\" encoding=\"ascii\"?>\r\n","<!-- keep display selection -->","<AdapterUID>-2147483647</AdapterUID>",
        "<MonitorUID>72</MonitorUID>","<RefreshRateNumerator>60000</RefreshRateNumerator>","<RefreshRateDenominator>1001</RefreshRateDenominator>",
        "<ScalingMode>Unspecified</ScalingMode>","<ScanlineMode>Progressive</ScanlineMode>","<StereoEyeDistance>0.012500</StereoEyeDistance>","<VSync>1</VSync>","<Option3DDepth>7</Option3DDepth>"};
    for(unsigned i=0;i<sizeof(untouched)/sizeof(*untouched);++i)CHECK(strstr(text,untouched[i]));
    free(text);
}
static char *replace(const char *in,const char *from,const char *to){
    const char *at=strstr(in,from);CHECK(at);size_t n=strlen(in)+strlen(to)+1;
    char *out=malloc(n);CHECK(out);size_t prefix=(size_t)(at-in);memcpy(out,in,prefix);strcpy(out+prefix,to);strcat(out,at+strlen(from));return out;
}
static void rejected_xml(const char *text){
    reset();put(target,text);CHECK(!sd_game_quality_apply(root,1));CHECK(sd_game_quality_error);
    same(target,text);CHECK(sdq_exists(backup)==0);same(sentinel,"save-and-UserOptions-unchanged\n");
}
static void recovered_original_or_light(void){
    CHECK(sdq_recover(target));CHECK(sdq_recover(backup));
    char *data=get(target),*light=NULL;size_t n=0;
    CHECK(sdq_light_xml(original_xml,strlen(original_xml),&light,&n));
    CHECK(!strcmp(data,original_xml)||!strcmp(data,light));free(data);free(light);
    if(sdq_exists(backup))same(backup,original_xml);
}
int main(void){
    char pattern[]="/tmp/sd-game-quality-XXXXXX";char *temp=mkdtemp(pattern);CHECK(temp);
    CHECK(strlen(temp)<sizeof(root));strcpy(root,temp);
    const char *directories[]={"/launcher","/drive_c","/drive_c/SleepingDogs","/drive_c/SleepingDogs/Data"};
    for(unsigned i=0;i<4;++i){char p[768];path(p,directories[i]);CHECK(!mkdir(p,0700));}
    path(target,"/drive_c/SleepingDogs/Data/DisplaySettings.xml");CHECK(sdq_path(backup,target,".fextendo-original"));
    path(modefile,"/launcher/game-quality.txt");path(sentinel,"/drive_c/SleepingDogs/Data/UserOptions.dat");
    reset();CHECK(sd_game_quality_load(root)==0);CHECK(sd_game_quality_apply(root,0));same(target,original_xml);
    CHECK(sd_game_quality_save(root,1));CHECK(sd_game_quality_load(root)==1);CHECK(sd_game_quality_apply(root,1));
    valid_light(target);same(backup,original_xml);same(sentinel,"save-and-UserOptions-unchanged\n");
    char *light=get(target);CHECK(sd_game_quality_apply(root,1));same(target,light);same(backup,original_xml);
    CHECK(sd_game_quality_apply(root,0));same(target,light);
    CHECK(sd_game_quality_restore(root));CHECK(sd_game_quality_load(root)==0);same(target,original_xml);same(backup,original_xml);free(light);
    CHECK(sd_game_quality_restore(root));same(target,original_xml);
    reset();CHECK(!unlink(target));CHECK(!sd_game_quality_apply(root,1));CHECK(strstr(sd_game_quality_error,"Open game once"));
    CHECK(sdq_exists(target)==sdq_exists(backup)&&sdq_exists(target)==0);CHECK(sd_game_quality_apply(root,0));
    CHECK(!sd_game_quality_restore(root));CHECK(sd_game_quality_load(root)==0);
    const char *malformed[]={"", "<Different/>","<!DOCTYPE DisplaySettings><DisplaySettings/>","<DisplaySettings><Version>1</Version></DisplaySettings>"};
    for(unsigned i=0;i<4;++i)rejected_xml(malformed[i]);
    const char *from[]={"<Version>1</Version>","<WorldDensity>2</WorldDensity>","<DisplaySettings>","<ShadowRes>3</ShadowRes>","<MotionBlur>1</MotionBlur>","<SSAO>2</SSAO>","</DisplaySettings>"};
    const char *to[]={"<Version>2</Version>","<WorldDensity>2</WorldDensity><WorldDensity>1</WorldDensity>","<DisplaySettings attr=\"x\">", "<ShadowRes><x>3</x></ShadowRes>","<MotionBlur>false</MotionBlur>","<SSAO>&zero;</SSAO>","<Unexpected>1</Unexpected></DisplaySettings>"};
    for(unsigned i=0;i<7;++i){char *bad=replace(original_xml,from[i],to[i]);rejected_xml(bad);free(bad);}
    const char *bad_global[]={"-2","--1","-01","-1junk","4294967296","1\n2"};
    for(unsigned i=0;i<sizeof(bad_global)/sizeof(*bad_global);++i){
        char tag[96];snprintf(tag,sizeof(tag),"<GlobalSetting>%s</GlobalSetting>",bad_global[i]);
        char *bad=replace(original_xml,"<GlobalSetting>4</GlobalSetting>",tag);rejected_xml(bad);free(bad);
        CHECK(strstr(sd_game_quality_error,"GlobalSetting"));CHECK(!strchr(sd_game_quality_error,'\n'));
    }
    char *negative=replace(original_xml,"<WorldDensity>2</WorldDensity>","<WorldDensity>-1</WorldDensity>");
    rejected_xml(negative);CHECK(strstr(sd_game_quality_error,"WorldDensity"));free(negative);
    char *custom=replace(original_xml,"<GlobalSetting>4</GlobalSetting>","<GlobalSetting> \t-1\r\n </GlobalSetting>");
    reset();put(target,custom);CHECK(sd_game_quality_apply(root,1));same(backup,custom);
    char *normalized=get(target);CHECK(strstr(normalized,"<GlobalSetting> \t0\r\n </GlobalSetting>"));free(normalized);
    CHECK(sd_game_quality_restore(root));same(target,custom);same(backup,custom);free(custom);
    char *bad_declaration=replace(original_xml,"<?xml version=\"1.0\" encoding=\"ascii\"?>","<?xml garbage?>");
    rejected_xml(bad_declaration);free(bad_declaration);
    reset();put(modefile,"1broken\n");CHECK(sd_game_quality_load(root)==0);same(modefile,"1broken\n");
    CHECK(!sd_game_quality_save(root,2));CHECK(!sd_game_quality_apply(root,-1));same(target,original_xml);
    reset();CHECK(sd_game_quality_apply(root,1));CHECK(sd_game_quality_save(root,1));put(backup,"broken");
    CHECK(!sd_game_quality_restore(root));CHECK(sd_game_quality_load(root)==0);valid_light(target);same(backup,"broken");
    CHECK(!sd_game_quality_apply(root,1));valid_light(target);same(backup,"broken");
    /* Single-operation failures across every write/flush/rename point. The
     * injected failure fires only once so immediate rollback can complete. */
    unsigned failure_cases=0;
    for(int kind=1;kind<=4;++kind){
        for(unsigned point=1;point<40;++point){
            reset();failure_kind=kind;fail_step=point;disk_step=0;int ok=sd_game_quality_apply(root,1);
            int fired=failure_fired;failure_kind=0;fail_step=0;
            if(!fired){CHECK(ok);break;}
            ++failure_cases;recovered_original_or_light();
            if(ok)valid_light(target);else same(target,original_xml);
            same(sentinel,"save-and-UserOptions-unchanged\n");
        }
    }
    /* Deferred old-file cleanup after commit must never revert save(1) to0. */
    reset();CHECK(sd_game_quality_save(root,0));failure_kind=4;fail_step=1;disk_step=0;
    CHECK(sd_game_quality_save(root,1));CHECK(failure_fired);failure_kind=0;fail_step=0;
    CHECK(sd_game_quality_load(root)==1);same(modefile,"1\n");
    /* Kill a separate process after every successful rename. The parent then
     * exercises recovery from disk bytes without the writer's stack state. */
    for(unsigned point=1;point<=5;++point){
        reset();pid_t child=fork();CHECK(child>=0);
        if(!child){failure_kind=99;disk_step=0;crash_step=point;sd_game_quality_apply(root,1);_exit(78);}
        int status=0;CHECK(waitpid(child,&status,0)==child);CHECK(WIFEXITED(status)&&WEXITSTATUS(status)==77);
        recovered_original_or_light();++power_cases;
        CHECK(sd_game_quality_apply(root,1));valid_light(target);same(backup,original_xml);
        CHECK(sd_game_quality_restore(root));same(target,original_xml);
    }
    /* Existing malformed journals are never interpreted or deleted. */
    reset();char journal[768];CHECK(sdq_path(journal,target,".sdq-txn"));put(journal,"foreign\n");
    CHECK(!sd_game_quality_apply(root,1));same(target,original_xml);same(journal,"foreign\n");
    reset();remove_artifacts(target);remove_artifacts(backup);remove_artifacts(modefile);CHECK(!unlink(sentinel));
    for(unsigned i=4;i>0;--i){char p[768];path(p,directories[i-1]);CHECK(!rmdir(p));}CHECK(!rmdir(root));
    printf("{\"status\":\"PASS\",\"checks\":%u,\"disk_failure_cases\":%u,\"write_failures\":%u,\"flush_failures\":%u,\"rename_failures\":%u,\"unlink_failures\":%u,\"interrupted_rename_cases\":%u,\"original_backup_preserved\":true,\"unrelated_fields_preserved\":true,\"missing_xml_refused\":true,\"restore_disables_enforcement\":true,\"committed_cleanup_cannot_revert_mode\":true}\n",checks,failure_cases,write_failures,flush_failures,rename_failures,unlink_failures,power_cases);
}
