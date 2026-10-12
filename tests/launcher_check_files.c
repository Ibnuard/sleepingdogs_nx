/* Real read-only validator against temporary game/runtime files. */
#include <assert.h>
#include <unistd.h>
#include <stdlib.h>
#include "system_check.h"
static int cancel;
static int stopped(void){return cancel;}
static void write_bytes(const char *p,const void *data,size_t n){FILE *f=fopen(p,"wb");assert(f);assert(fwrite(data,1,n,f)==n);assert(!fclose(f));}
int main(int argc,char** argv){
    assert(argc==2);assert(!chdir(argv[1]));
    struct sd_check_job j={.root=argv[1],.cancelled=stopped};
    assert(!sd_check_game(&j));
    unsigned char pe[256]={0};pe[0]='M';pe[1]='Z';pe[60]=64;memcpy(pe+64,"PE\0\0",4);pe[68]=0x4c;pe[69]=1;pe[88]=11;pe[89]=1;
    const char *exe="drive_c/SleepingDogs/HKShip.exe";write_bytes(exe,pe,sizeof(pe));assert(sd_check_pe32(exe));
    assert(!sd_check_game(&j));
    const char *names[]={"Game.big","Game.bix","Global.big","Global.bix","UI.big","UI.bix","SeekFreeBoot.big","SeekFreeBoot.bix","Animation.big","Animation.bix","Characters.big","Characters.bix","Vehicles.big","Vehicles.bix","binkw32.dll"};
    char p[256];for(unsigned i=0;i<15;i++){snprintf(p,sizeof(p),"drive_c/SleepingDogs/%s",names[i]);write_bytes(p,"game fixture",12);}
    assert(sd_check_game(&j));pe[89]=2;write_bytes(exe,pe,sizeof(pe));assert(!sd_check_game(&j));
    pe[89]=1;write_bytes(exe,pe,sizeof(pe));pe[60]=255;write_bytes(exe,pe,sizeof(pe));assert(!sd_check_pe32(exe));
    pe[60]=64;write_bytes(exe,pe,sizeof(pe));
    assert(!sd_check_runtime(&j));write_bytes("runtime.dll","runtime",7);assert(sd_check_runtime(&j));
    write_bytes("runtime.dll","runtimE",7);assert(!sd_check_runtime(&j));
    write_bytes("runtime.dll","different",9);assert(sd_check_runtime(&j));
    cancel=1;assert(!sd_check_runtime(&j));cancel=0;
    assert(!unlink("runtime.dll"));assert(!symlink("drive_c/SleepingDogs/Game.big","runtime.dll"));assert(!sd_check_runtime(&j));
    assert(!unlink("runtime.dll"));assert(!mkdir("runtime.dll",0700));assert(!sd_check_runtime(&j));
    puts("PASS: missing/invalid PE32 and game files, exact runtime digest, approved A/B digest, corruption, cancellation, symlink/directory rejection");
}
