/* SPDX-License-Identifier: LGPL-2.1-or-later.
 * Cache successful full-file verification, not the current boot/mapping probe.
 * Metadata is a change detector, not an authenticity or corruption guarantee.
 */
#ifndef SD_CHECK_CACHE_H
#define SD_CHECK_CACHE_H
#include <unistd.h>
#ifndef SD_CHECK_CACHE_BUILD
#define SD_CHECK_CACHE_BUILD "launcher-cache-v2-test"
#endif
static int sd_check_cache_path(struct sd_check_job *j,char *path,size_t cap){
    return sd_check_path(path,cap,j->root,"launcher/system-check-v2.cache");
}
static void sd_check_cache_invalidate(struct sd_check_job *j){
    char path[1024];if(sd_check_cache_path(j,path,sizeof(path)))unlink(path);
}
static int sd_check_signature(struct sd_check_job *j,unsigned char hash[32]){
    Sha256Context ctx;sha256ContextCreate(&ctx);
    sha256ContextUpdate(&ctx,SD_CHECK_CACHE_BUILD,sizeof(SD_CHECK_CACHE_BUILD));
    for(unsigned i=0;i<SD_CHECK_FILE_COUNT;i++){
        char path[1024];uint64_t bytes;struct stat st;
        const struct sd_check_file *file=&sd_check_files[i];
        if((j->cancelled&&j->cancelled())||!sd_check_path(path,sizeof(path),j->root,file->path)||
           !sd_check_regular(path,&bytes)||lstat(path,&st))return 0;
        /* Serialized fields avoid struct padding and remain stable on FAT. */
        uint64_t metadata[2]={bytes,(uint64_t)st.st_mtime};
        sha256ContextUpdate(&ctx,file->path,strlen(file->path)+1);
        sha256ContextUpdate(&ctx,file->sha256,strlen(file->sha256)+1);
        if(file->alternate_sha256)sha256ContextUpdate(&ctx,file->alternate_sha256,strlen(file->alternate_sha256)+1);
        sha256ContextUpdate(&ctx,metadata,sizeof(metadata));
    }
    sha256ContextGetHash(&ctx,hash);return 1;
}
static int sd_check_cache_matches(struct sd_check_job *j,const unsigned char signature[32]){
    char path[1024];unsigned char record[40];uint64_t size;
    if(!sd_check_cache_path(j,path,sizeof(path))||!sd_check_regular(path,&size)||size!=sizeof(record))return 0;
    FILE *f=fopen(path,"rb");if(!f)return 0;
    int ok=fread(record,1,sizeof(record),f)==sizeof(record)&&fgetc(f)==EOF&&!ferror(f);
    fclose(f);return ok&&!memcmp(record,"SDCHECK2",8)&&!memcmp(record+8,signature,32);
}
static int sd_check_cache_save(struct sd_check_job *j,const unsigned char signature[32]){
    char path[1024],stage[1040];unsigned char record[40];
    if(!sd_check_cache_path(j,path,sizeof(path)))return 0;
    snprintf(stage,sizeof(stage),"%s.new",path);memcpy(record,"SDCHECK2",8);memcpy(record+8,signature,32);
    FILE *f=fopen(stage,"wb");if(!f)return 0;
    int ok=fwrite(record,1,sizeof(record),f)==sizeof(record)&&!fflush(f);
    if(ok&&fsync(fileno(f)))ok=0;
    if(fclose(f))ok=0;
    if(ok&&rename(stage,path))ok=0;
    if(!ok)unlink(stage);return ok;
}
static int sd_check_runtime_cached(struct sd_check_job *j,int force,int *hit,int *saved){
    unsigned char before[32],after[32];*hit=*saved=0;
    int fingerprint=sd_check_signature(j,before);
    if(!force&&fingerprint&&sd_check_cache_matches(j,before)){*hit=1;return 1;}
    sd_check_cache_invalidate(j);
    if(!sd_check_runtime(j))return 0;
    if(!fingerprint||!sd_check_signature(j,after)||memcmp(before,after,32)){
        snprintf(j->error,sizeof(j->error),"Runtime files changed during verification. Retry System Check.");return 0;
    }
    *saved=sd_check_cache_save(j,after);return 1;
}
#endif
