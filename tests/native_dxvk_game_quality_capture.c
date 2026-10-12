/* SPDX-License-Identifier: MIT; replay exact user XML against old/current helper. */
#define _GNU_SOURCE
#include <assert.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
static void log_line(const char *format,...){(void)format;}
#include "game_quality.h"
static void same(const char *path,const char *expected,size_t length){
    char *actual=NULL;size_t n=0;assert(sdq_read(path,&actual,&n)==1);
    assert(n==length&&!memcmp(actual,expected,n));free(actual);
}
int main(int argc,char **argv){
    assert(argc==2);char *original=NULL;size_t length=0;assert(sdq_read(argv[1],&original,&length)==1);
    const char *needle="<GlobalSetting>-1</GlobalSetting>";
    char *at=strstr(original,needle);assert(at&&!strstr(at+1,needle));
    size_t offset=(size_t)(at-original)+strlen("<GlobalSetting>");
    char *expected=malloc(length);assert(expected);
    memcpy(expected,original,offset);expected[offset]='0';memcpy(expected+offset+1,original+offset+2,length-offset-1);
    char root[]="/tmp/sd-quality-capture-XXXXXX";assert(mkdtemp(root));
    char path[768],backup[768],mode[768];
    const char *dirs[]={"/launcher","/drive_c","/drive_c/SleepingDogs","/drive_c/SleepingDogs/Data"};
    for(unsigned i=0;i<4;++i){assert(sdq_path(path,root,dirs[i]));assert(!mkdir(path,0700));}
    assert(sdq_path(path,root,"/drive_c/SleepingDogs/Data/DisplaySettings.xml"));
    assert(sdq_path(backup,path,".fextendo-original"));assert(sdq_path(mode,root,"/launcher/game-quality.txt"));
    assert(sdq_write_new(path,original,length));int ok=sd_game_quality_apply(root,1);
    if(!ok){
        same(path,original,length);assert(!sdq_exists(backup));
        printf("REJECTED_PRESERVED: %s\n",sd_game_quality_error);
    }else{
        /* Every byte except the two-byte -1 -> one-byte 0 is unchanged. */
        same(path,expected,length-1);same(backup,original,length);
        assert(sd_game_quality_apply(root,1));same(path,expected,length-1);same(backup,original,length);
        assert(sd_game_quality_apply(root,0));same(path,expected,length-1);
        assert(sd_game_quality_restore(root));assert(sd_game_quality_load(root)==0);
        same(path,original,length);same(backup,original,length);assert(sd_game_quality_apply(root,1));
        same(path,expected,length-1);same(backup,original,length);
        assert(!unlink(backup));assert(!unlink(mode));
        puts("PASS: exact supplied XML; only GlobalSetting -1 to0; repeated apply and byte-exact original restore");
    }
    assert(!unlink(path));
    for(unsigned i=4;i>0;--i){assert(sdq_path(path,root,dirs[i-1]));assert(!rmdir(path));}assert(!rmdir(root));
    free(original);free(expected);return ok?0:42;
}
