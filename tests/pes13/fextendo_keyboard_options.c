/* File persistence/recovery, with no game or platform dependency. */
#include <assert.h>
#include "../src/runtime/fextendo_presets.h"
int main(int argc,char **argv) {
    assert(!fx_keyboard_options.shortcut&&!fx_keyboard_options.top&&!fx_keyboard_options.hold_ms);
    assert(argc==2);const char *root=argv[1];char path[800],old[800];
    struct fx_keyboard_options value=fx_keyboard_options_load(root);
    assert(!value.shortcut&&!value.top&&!value.hold_ms);
    for(int s=0;s<FX_KEYBOARD_SHORTCUTS;s++)for(int top=0;top<2;top++)for(int h=0;h<FX_KEYBOARD_HOLD_CHOICES;h++){
        int ms=(int)fx_keyboard_hold_ms[h];
        assert(fx_keyboard_options_save(root,(struct fx_keyboard_options){s,top,ms}));
        value=fx_keyboard_options_load(root);assert(value.shortcut==s&&value.top==top&&value.hold_ms==ms);
    }
    assert(!fx_keyboard_options_save(root,(struct fx_keyboard_options){FX_KEYBOARD_SHORTCUTS,0,0}));
    assert(!fx_keyboard_options_save(root,(struct fx_keyboard_options){0,-1,0}));
    assert(!fx_keyboard_options_save(root,(struct fx_keyboard_options){0,0,42}));
    assert(!fx_keyboard_options_save(root,(struct fx_keyboard_options){0,0,-1}));
    snprintf(path,sizeof(path),"%s/launcher/keyboard.ini",root);
    snprintf(old,sizeof(old),"%s/launcher/keyboard.ini.old",root);
    assert(!rename(path,old)); /* Power loss between the two renames. */
    value=fx_keyboard_options_load(root);assert(value.shortcut==FX_KEYBOARD_SHORTCUTS-1&&value.top==1&&value.hold_ms==2000);
    assert(fx_write(path,"[keyboard]\nshortcut=99\ntop=0\n",28));
    value=fx_keyboard_options_load(root);assert(value.shortcut==FX_KEYBOARD_SHORTCUTS-1&&value.top==1&&value.hold_ms==2000);
    assert(fx_keyboard_options_save(root,(struct fx_keyboard_options){1,0,300}));
    value=fx_keyboard_options_load(root);assert(value.shortcut==1&&!value.top&&value.hold_ms==300);
    assert(access(old,F_OK));
    const char *legacy="[keyboard]\nshortcut=2\ntop=1\n";
    assert(fx_write(path,legacy,strlen(legacy)));
    value=fx_keyboard_options_load(root);assert(value.shortcut==2&&value.top==1&&!value.hold_ms);
    char check[128]={0};assert(fx_read(path,check,sizeof(check))==strlen(legacy)&&!strcmp(check,legacy));
    const char *disabled="[keyboard]\nshortcut=4\ntop=0\n";
    assert(fx_write(path,disabled,strlen(disabled)));
    value=fx_keyboard_options_load(root);assert(value.shortcut==FX_KEYBOARD_DISABLED);
    assert(value.shortcut!=FX_KEYBOARD_CAPTURE); /* old Disabled never becomes Capture */
    const char *bad[]={"[keyboard]\nshortcut=2\ntop=1\nhold_ms=-1\n",
        "[keyboard]\nshortcut=2\ntop=1\nhold_ms=2010\n", "[keyboard]\nshortcut=2\ntop=1\nhold_ms=1\n",
        "[keyboard]\nshortcut=2\ntop=1\nhold_ms=300\ngarbage\n"};
    for(unsigned i=0;i<sizeof(bad)/sizeof(*bad);i++){
        assert(fx_write(path,bad[i],strlen(bad[i])));assert(!fx_keyboard_options_read(path,&value));
    }
    /* Instant fires on the first complete chord, holds fire at the threshold,
     * never repeat while held, and require a release after focus suppression. */
    for(unsigned choice=0;choice<4;choice++)for(unsigned h=0;h<FX_KEYBOARD_HOLD_CHOICES;h++){
        uint64_t mask=fx_keyboard_chord_mask(choice,FX_PAD_FULL),now=0;
        unsigned ms=fx_keyboard_hold_ms[h];struct fx_keyboard_chord chord={0};
        assert(fx_keyboard_chord_poll(&chord,mask,mask,now,1,ms)==(ms==0));
        if(ms){
            assert(!fx_keyboard_chord_poll(&chord,mask,mask,ms-1,1,ms));
            assert(fx_keyboard_chord_poll(&chord,mask,mask,ms,1,ms));
        }
        assert(!fx_keyboard_chord_poll(&chord,mask,mask,ms+3000,1,ms));
        assert(!fx_keyboard_chord_poll(&chord,0,mask,ms+3001,1,ms));
        assert(!fx_keyboard_chord_poll(&chord,mask,mask,ms+3002,0,ms));
        assert(!fx_keyboard_chord_poll(&chord,mask,mask,ms+6000,1,ms));
        assert(!fx_keyboard_chord_poll(&chord,0,mask,ms+6001,1,ms));
        assert(fx_keyboard_chord_poll(&chord,mask,mask,ms+6002,1,ms)==(ms==0));
    }
    for(int kind=FX_PAD_FULL;kind<=FX_PAD_HANDHELD;kind++){
        assert(!fx_keyboard_chord_mask(FX_KEYBOARD_DISABLED,kind));
        assert(!fx_keyboard_chord_mask(FX_KEYBOARD_CAPTURE,kind));
    }
    puts("PASS: all shortcut/delay/position combinations, read-only legacy migration, invalid values, recovery, instant edge, exact hold thresholds, no repeat and focus rearm");
}
