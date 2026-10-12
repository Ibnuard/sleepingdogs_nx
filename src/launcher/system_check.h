/* SPDX-License-Identifier: LGPL-2.1-or-later.
 * Adapted from PES13 fextendo_install_check.h/runtime_fixer.h. Offline only;
 * game payloads and saves are never modified. The catalog is built into NRO.
 */
#ifndef SD_SYSTEM_CHECK_H
#define SD_SYSTEM_CHECK_H
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <errno.h>
#ifdef __SWITCH__
#include <switch.h>
#else
#include <openssl/sha.h>
typedef SHA256_CTX Sha256Context;
#define sha256ContextCreate SHA256_Init
#define sha256ContextUpdate SHA256_Update
#define sha256ContextGetHash(c,h) SHA256_Final(h,c)
#endif
enum sd_check_stage {SD_CHECK_BOOT,SD_CHECK_PATCH,SD_CHECK_GAME,SD_CHECK_RUNTIME,SD_CHECK_ART};
struct sd_check_view {int visible,failed,complete,stage,percent,done[4];char error[192];};
struct sd_check_file {const char *path;uint64_t bytes;const char *sha256;const char *alternate_sha256;};
#include "system_catalog.h"
struct sd_check_job {const char *root;int (*cancelled)(void);void (*progress)(int,int);char error[192];};
static int sd_check_fail(struct sd_check_job *j,const char *what,const char *path){
    snprintf(j->error,sizeof(j->error),"%s%s. Recopy the complete Sleeping Dogs runtime update.",what,path);return 0;
}
static int sd_check_path(char *out,size_t cap,const char *root,const char *rel){
    int n=snprintf(out,cap,"%s/%s",root,rel);return n>0&&(size_t)n<cap;
}
static int sd_check_regular(const char *path,uint64_t *bytes){
    char p[1024];struct stat st;size_t length=strlen(path);if(length>=sizeof(p))return 0;
    memcpy(p,path,length+1);
    for(char *s=p+1;*s;s++)if(*s=='/'&&s[-1]!=':'){
        *s=0;int valid=!lstat(p,&st)&&S_ISDIR(st.st_mode);*s='/';if(!valid)return 0;
    }
    if(lstat(path,&st)||!S_ISREG(st.st_mode)||st.st_size<=0)return 0;
    *bytes=st.st_size;return 1;
}
static int sd_check_pe32(const char *path){
    unsigned char dos[64],pe[26];uint64_t size;int valid=0;
    if(!sd_check_regular(path,&size))return 0;
    FILE *f=fopen(path,"rb");if(!f)return 0;
    if(fread(dos,1,64,f)==64&&dos[0]=='M'&&dos[1]=='Z'){
        uint32_t at=(uint32_t)dos[60]|(uint32_t)dos[61]<<8|(uint32_t)dos[62]<<16|(uint32_t)dos[63]<<24;
        if(at>=64&&(uint64_t)at+26<=size&&!fseek(f,at,SEEK_SET)&&fread(pe,1,26,f)==26)
            valid=!memcmp(pe,"PE\0\0",4)&&pe[4]==0x4c&&pe[5]==1&&pe[24]==0x0b&&pe[25]==1;
    }
    fclose(f);return valid;
}
static int sd_check_game(struct sd_check_job *j){
    char path[1024];struct stat st;uint64_t bytes;
    if(!sd_check_path(path,sizeof(path),j->root,"drive_c/SleepingDogs/HKShip.exe")||!sd_check_pe32(path)){
        snprintf(j->error,sizeof(j->error),"Missing/invalid drive_c/SleepingDogs/HKShip.exe. Copy the original 32-bit Sleeping Dogs PC game.");return 0;
    }
    static const char *const required[]={"Game.big","Game.bix","Global.big","Global.bix","UI.big","UI.bix",
        "SeekFreeBoot.big","SeekFreeBoot.bix","Animation.big","Animation.bix","Characters.big","Characters.bix","Vehicles.big","Vehicles.bix","binkw32.dll"};
    for(unsigned i=0;i<sizeof(required)/sizeof(*required);i++){
        char rel[128];snprintf(rel,sizeof(rel),"drive_c/SleepingDogs/%s",required[i]);
        if(!sd_check_path(path,sizeof(path),j->root,rel)||!sd_check_regular(path,&bytes)){
            snprintf(j->error,sizeof(j->error),"Missing/unreadable %s. Copy the complete game folder.",required[i]);return 0;
        }
    }
    sd_check_path(path,sizeof(path),j->root,"drive_c/SleepingDogs/Data");
    if(lstat(path,&st)||!S_ISDIR(st.st_mode)){
        snprintf(j->error,sizeof(j->error),"Missing SleepingDogs/Data folder. Copy the complete game folder.");return 0;
    }
    return 1;
}
static int sd_check_runtime(struct sd_check_job *j){
    char path[1024],hex[65];unsigned char buffer[32768],hash[32];
    static const char digits[]="0123456789abcdef";
    for(unsigned i=0;i<SD_CHECK_FILE_COUNT;i++){
        if(j->cancelled&&j->cancelled())return 0;
        if(j->progress)j->progress(SD_CHECK_RUNTIME,(int)(i*100/SD_CHECK_FILE_COUNT));
        const struct sd_check_file *file=&sd_check_files[i];uint64_t bytes,read=0;
        if(!sd_check_path(path,sizeof(path),j->root,file->path)||!sd_check_regular(path,&bytes)||
           (bytes!=file->bytes&&!(file->alternate_sha256&&*file->alternate_sha256)))
            return sd_check_fail(j,"Missing/incomplete ",file->path);
        FILE *f=fopen(path,"rb");if(!f)return sd_check_fail(j,"Cannot read ",file->path);
        Sha256Context ctx;sha256ContextCreate(&ctx);size_t n;int ok=1;
        while((n=fread(buffer,1,sizeof(buffer),f))){
            if((j->cancelled&&j->cancelled())||(read+=n)>bytes){ok=0;break;}
            sha256ContextUpdate(&ctx,buffer,n);
        }
        if(ferror(f)||read!=bytes)ok=0;
        fclose(f);sha256ContextGetHash(&ctx,hash);
        for(int k=0;k<32;k++){hex[2*k]=digits[hash[k]>>4];hex[2*k+1]=digits[hash[k]&15];}hex[64]=0;
        if(!ok||(strcmp(hex,file->sha256)&&(!file->alternate_sha256||strcmp(hex,file->alternate_sha256))))
            return sd_check_fail(j,"Wrong version/damaged ",file->path);
    }
    return 1;
}
#endif
