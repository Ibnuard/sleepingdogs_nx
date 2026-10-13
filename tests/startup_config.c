/* Exercise real missing-file repair with interrupted writes and user overrides. */
#include <assert.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/stat.h>
static int write_fault,write_calls;
static ssize_t fixture_write(int fd,const void *data,size_t bytes){
    if(write_fault){if(write_calls++){errno=ENOSPC;return -1;}return write(fd,data,bytes/2);}
    return write(fd,data,bytes);
}
#define write fixture_write
#include "startup_config.h"
#undef write
static void put(const char *path,const void *data,size_t bytes){
    FILE *f=fopen(path,"wb");assert(f);assert(fwrite(data,1,bytes,f)==bytes);assert(!fclose(f));
}
static void equal(const char *path,const void *data,size_t bytes){
    unsigned char got[4096];FILE *f=fopen(path,"rb");assert(f);
    assert(fread(got,1,sizeof(got),f)==bytes&&!ferror(f));assert(!memcmp(got,data,bytes));assert(!fclose(f));
}
int main(int argc,char **argv){
    assert(argc==2&&!chdir(argv[1]));char error[192];struct stat st;
    assert(!mkdir("drive_c",0700));assert(!mkdir("drive_c/SleepingDogs",0700));
    assert(sd_startup_config_restore(".",error,sizeof(error)));
    const char *folder="drive_c/SleepingDogs/.pandora";char path[256];
    for(unsigned i=0;i<3;i++){
        snprintf(path,sizeof(path),"%s/%s",folder,sd_startup_files[i].name);
        equal(path,sd_startup_files[i].data,sd_startup_files[i].bytes);
    }
    assert(sd_startup_config_restore(".",error,sizeof(error))); /* Empty local is valid. */
    snprintf(path,sizeof(path),"%s/config.json",folder);put(path,"user override",13);
    assert(sd_startup_config_restore(".",error,sizeof(error)));equal(path,"user override",13);
    char marker[256];snprintf(marker,sizeof(marker),"%s/local",folder);assert(!unlink(marker));
    assert(sd_startup_config_restore(".",error,sizeof(error)));equal(marker,"",0);equal(path,"user override",13);
    /* Failed partial write cannot publish a partial config. Retry uses defaults. */
    assert(!unlink(path));write_fault=1;write_calls=0;
    assert(!sd_startup_config_restore(".",error,sizeof(error))&&strstr(error,"config.json"));
    assert(lstat(path,&st)&&errno==ENOENT);
    char stage[288];snprintf(stage,sizeof(stage),"%s.fextendo-new",path);
    assert(lstat(stage,&st)&&errno==ENOENT);write_fault=0;
    put(stage,"interrupted",11);assert(sd_startup_config_restore(".",error,sizeof(error)));
    equal(path,sd_startup_config_json,sizeof(sd_startup_config_json));assert(lstat(stage,&st)&&errno==ENOENT);
    /* Unsafe objects are rejected and remain untouched. */
    assert(!unlink(marker));assert(!mkdir(marker,0700));
    assert(!sd_startup_config_restore(".",error,sizeof(error))&&strstr(error,"local"));
    assert(!rmdir(marker));assert(!symlink("config.json",marker));
    assert(!sd_startup_config_restore(".",error,sizeof(error)));assert(!lstat(marker,&st)&&S_ISLNK(st.st_mode));
    assert(!unlink(marker));assert(sd_startup_config_restore(".",error,sizeof(error)));
    put(path,"",0);assert(!sd_startup_config_restore(".",error,sizeof(error)));equal(path,"",0);
    puts("PASS missing/partial repair, exact bytes incl. empty local, repeat launch, preserve overrides, ENOSPC cleanup, stale staging recovery, directory/symlink rejection");
}
