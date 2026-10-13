/* SPDX-License-Identifier: LGPL-2.1-or-later.
 * Restore missing startup configuration from the NRO, preserving user files.
 */
#ifndef SD_STARTUP_CONFIG_H
#define SD_STARTUP_CONFIG_H
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#include "startup_config_data.h"

static int sd_startup_config_error(char *error,size_t cap,const char *name){
    snprintf(error,cap,"Cannot read/restore .pandora/%s. Check SD free space and write access, then retry.",name);
    return 0;
}
static int sd_startup_config_restore(const char *root,char *error,size_t cap){
    char directory[1024],path[1088],stage[1120];struct stat st;
    int n=snprintf(directory,sizeof(directory),"%s/drive_c/SleepingDogs/.pandora",root);
    if(n<0||(size_t)n>=sizeof(directory))return sd_startup_config_error(error,cap,"folder");
    if(lstat(directory,&st)){
        if(errno!=ENOENT||mkdir(directory,0777)||lstat(directory,&st))
            return sd_startup_config_error(error,cap,"folder");
    }
    if(!S_ISDIR(st.st_mode))return sd_startup_config_error(error,cap,"folder");
    for(unsigned i=0;i<sizeof(sd_startup_files)/sizeof(*sd_startup_files);++i){
        const struct sd_startup_file *item=&sd_startup_files[i];
        snprintf(path,sizeof(path),"%s/%s",directory,item->name);
        if(!lstat(path,&st)){
            if(!S_ISREG(st.st_mode)||(item->bytes&&st.st_size==0))
                return sd_startup_config_error(error,cap,item->name);
            FILE *f=fopen(path,"rb");if(!f)return sd_startup_config_error(error,cap,item->name);
            int ok=!fclose(f);if(!ok)return sd_startup_config_error(error,cap,item->name);
            continue;
        }
        if(errno!=ENOENT)return sd_startup_config_error(error,cap,item->name);
        /* Recover only our own interrupted staging file, never user config. */
        snprintf(stage,sizeof(stage),"%s.fextendo-new",path);
        if(!lstat(stage,&st)){
            if(!S_ISREG(st.st_mode)||unlink(stage))return sd_startup_config_error(error,cap,item->name);
        }else if(errno!=ENOENT)return sd_startup_config_error(error,cap,item->name);
        int fd=open(stage,O_WRONLY|O_CREAT|O_EXCL,0666);
        if(fd<0)return sd_startup_config_error(error,cap,item->name);
        size_t written=0;int ok=1;
        while(written<item->bytes){
            ssize_t count=write(fd,item->data+written,item->bytes-written);
            if(count<0&&errno==EINTR)continue;
            if(count<=0){ok=0;break;}written+=(size_t)count;
        }
        if(ok&&fsync(fd))ok=0;
        if(close(fd))ok=0;
        if(ok&&rename(stage,path))ok=0;
        if(!ok){unlink(stage);return sd_startup_config_error(error,cap,item->name);}
    }
    return 1;
}
#endif
