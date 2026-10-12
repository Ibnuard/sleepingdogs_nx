/* SPDX-License-Identifier: LGPL-2.1-or-later. From pinned PES13 launcher. */
#include "pes13/fextendo_keyboard_options.h"
static int fx_keyboard_options_read(const char *path,struct fx_keyboard_options *out) {
    char data[128]={0};unsigned shortcut,top,hold=0;int end=0,tail=0;
    size_t n=fx_read(path,data,sizeof(data)-1);
    if(!n||sscanf(data,"[keyboard]\nshortcut=%u\ntop=%u\n%n",&shortcut,&top,&end)!=2||
       shortcut>=FX_KEYBOARD_SHORTCUTS||top>1)return 0;
    /* Existing two-field files keep their shortcut/position and get Instant.
     * Do not rewrite preferences just because a new build was opened. */
    if(end!=(int)n&&(sscanf(data+end,"hold_ms=%u\n%n",&hold,&tail)!=1||end+tail!=(int)n))return 0;
    if(hold>2000||fx_keyboard_hold_index((int)hold)<0)return 0;
    *out=(struct fx_keyboard_options){(int)shortcut,(int)top,(int)hold};return 1;
}
static struct fx_keyboard_options fx_keyboard_options_load(const char *root) {
    struct fx_keyboard_options out={0};char path[800];
    snprintf(path,sizeof(path),"%s/launcher/keyboard.ini",root);
    if(fx_keyboard_options_read(path,&out))return out;
    snprintf(path,sizeof(path),"%s/launcher/keyboard.ini.old",root);
    fx_keyboard_options_read(path,&out);return out;
}
static int fx_keyboard_options_save(const char *root,struct fx_keyboard_options value) {
    char path[768],old[800],tmp[800],text[80];struct fx_keyboard_options previous;
    if(value.shortcut<0||value.shortcut>=FX_KEYBOARD_SHORTCUTS||value.top<0||value.top>1||
       fx_keyboard_hold_index(value.hold_ms)<0)return 0;
    snprintf(path,sizeof(path),"%s/launcher/keyboard.ini",root);
    snprintf(old,sizeof(old),"%s.old",path);snprintf(tmp,sizeof(tmp),"%s.new",path);
    int n=snprintf(text,sizeof(text),"[keyboard]\nshortcut=%d\ntop=%d\nhold_ms=%d\n",value.shortcut,value.top,value.hold_ms);
    if(!fx_mkdir_parents(path)||!fx_write(tmp,text,(size_t)n))return 0;
    if(fx_keyboard_options_read(path,&previous)){
        if(unlink(old)&&errno!=ENOENT)return 0;
        if(rename(path,old))return 0;
    }else if(unlink(path)&&errno!=ENOENT)return 0;
    if(rename(tmp,path)){rename(old,path);return 0;}
    unlink(old);return 1;
}
static int fx_debug_launch(const char *root) {
    char p[768],b[2];snprintf(p,sizeof(p),"%s/launcher/debug-launch.txt",root);
    return fx_read(p,b,2)==2&&b[0]=='1'&&b[1]=='\n';
}
static int fx_debug_launch_save(const char *root,int on) {
    char p[768];snprintf(p,sizeof(p),"%s/launcher/debug-launch.txt",root);
    return fx_write(p,on?"1\n":"0\n",2);
}
