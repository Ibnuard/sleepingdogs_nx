/* Real file cache: force verification, update invalidation and failure recovery. */
#include <assert.h>
#include <stdlib.h>
#include <unistd.h>
#include <utime.h>
#include "system_check.h"
#include "check_cache.h"
static unsigned hashes;
static int cancel;
static int cancelled(void){return cancel;}
static void progress(int stage,int percent){assert(stage==SD_CHECK_RUNTIME);(void)percent;hashes++;}
static void write_file(const char *path,const char *s){FILE *f=fopen(path,"wb");assert(f);assert(fwrite(s,1,strlen(s),f)==strlen(s));assert(!fclose(f));}
int main(int argc,char **argv){
    assert(argc==2&&!chdir(argv[1]));
    struct sd_check_job j={.root=argv[1],.cancelled=cancelled,.progress=progress};
    int hit,saved;
    write_file("runtime.dll","runtime");
    assert(sd_check_runtime_cached(&j,0,&hit,&saved)&&!hit&&saved&&hashes==1);
    hashes=0;assert(sd_check_runtime_cached(&j,0,&hit,&saved)&&hit&&!hashes);
    assert(sd_check_runtime_cached(&j,1,&hit,&saved)&&!hit&&saved&&hashes==1);
    /* Same size, changed FAT-compatible whole-second timestamp invalidates. */
    struct stat st;assert(!stat("runtime.dll",&st));
    struct utimbuf times={st.st_atime,st.st_mtime+4};assert(!utime("runtime.dll",&times));
    hashes=0;assert(sd_check_runtime_cached(&j,0,&hit,&saved)&&!hit&&saved&&hashes==1);
    write_file("runtime.dll","different");
    assert(sd_check_runtime_cached(&j,0,&hit,&saved)&&!hit&&saved);
    write_file("runtime.dll","bad");
    assert(!sd_check_runtime_cached(&j,0,&hit,&saved));assert(access("launcher/system-check-v2.cache",F_OK));
    write_file("runtime.dll","runtime");assert(sd_check_runtime_cached(&j,0,&hit,&saved)&&saved);
    write_file("launcher/system-check-v2.cache","truncated");
    assert(sd_check_runtime_cached(&j,0,&hit,&saved)&&!hit&&saved);
    /* Catalog/build changes cannot reuse a prior version's completion record. */
    unsigned char signature[32];assert(sd_check_signature(&j,signature));signature[0]^=1;
    assert(sd_check_cache_save(&j,signature));
    assert(sd_check_runtime_cached(&j,0,&hit,&saved)&&!hit&&saved);
    cancel=1;assert(!sd_check_runtime_cached(&j,0,&hit,&saved));assert(access("launcher/system-check-v2.cache",F_OK));cancel=0;
    assert(sd_check_runtime_cached(&j,0,&hit,&saved)&&saved);
    assert(!unlink("runtime.dll"));assert(!sd_check_runtime_cached(&j,0,&hit,&saved));
    puts("PASS: first full hash, cached repeat without hashing, manual recheck, timestamp/size/update invalidation, approved A/B file, corruption, truncated/mismatched cache, cancellation and missing file");
}
