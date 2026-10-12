/* LGPL-2.1-or-later. Shared launcher/runtime keyboard preferences. */
#ifndef FEXTENDO_KEYBOARD_OPTIONS_H
#define FEXTENDO_KEYBOARD_OPTIONS_H
#include "fextendo_gamepad.h"
#define FX_KEYBOARD_DISABLED 4
/* Keep stored values 0..4 unchanged for existing keyboard.ini files. */
#define FX_KEYBOARD_CAPTURE 5
#define FX_KEYBOARD_SHORTCUTS 6
#define FX_KEYBOARD_HOLD_CHOICES 6
static const unsigned fx_keyboard_hold_ms[FX_KEYBOARD_HOLD_CHOICES]={0,300,600,1000,1500,2000};
static const char *const fx_keyboard_hold_names[FX_KEYBOARD_HOLD_CHOICES]={
    "Instant", "0.3 seconds", "0.6 seconds", "1 second", "1.5 seconds", "2 seconds"};
static const char *const fx_keyboard_shortcut_names[FX_KEYBOARD_SHORTCUTS]={
    "L + R + Left Stick", "+ and -", "L + R + Plus", "ZL + ZR + Minus", "Disabled", "Capture (Screenshot)"};
struct fx_keyboard_options { int shortcut,top,hold_ms; };
static struct fx_keyboard_options fx_keyboard_options;
static int fx_keyboard_hold_index(int ms) {
    for(int i=0;i<FX_KEYBOARD_HOLD_CHOICES;i++)if(ms==(int)fx_keyboard_hold_ms[i])return i;
    return -1;
}
struct fx_keyboard_chord { uint64_t since; int tracking,fired; };
static uint64_t fx_keyboard_chord_mask(int choice,int kind) {
    if(choice<0||choice>=FX_KEYBOARD_DISABLED)return 0;
    /* A horizontal Joy-Con has one +/- button and one stick. Its normalized
     * SL/SR + Stick chord remains available for every enabled choice. */
    if(kind==FX_PAD_LEFT||kind==FX_PAD_RIGHT)return FX_PAD_L|FX_PAD_R|FX_PAD_LSTICK;
    const uint64_t masks[]={FX_PAD_L|FX_PAD_R|FX_PAD_LSTICK,FX_PAD_PLUS|FX_PAD_MINUS,
        FX_PAD_L|FX_PAD_R|FX_PAD_PLUS,FX_PAD_ZL|FX_PAD_ZR|FX_PAD_MINUS};
    return masks[choice];
}
/* Only detects a request. It never suppresses gamepad input. Rearm on chord
 * release, independently of analog motion or the other player's controls. */
static int fx_keyboard_chord_poll(struct fx_keyboard_chord *s,uint64_t buttons,
                                  uint64_t mask,uint64_t now,int enabled,unsigned hold_ms) {
    if(!mask||(buttons&mask)!=mask){memset(s,0,sizeof(*s));return 0;}
    if(!enabled){s->fired=1;s->tracking=0;return 0;}
    if(s->fired)return 0;
    if(!s->tracking){s->tracking=1;s->since=now;}
    if(now-s->since<hold_ms)return 0;
    s->fired=1;return 1;
}
#endif
