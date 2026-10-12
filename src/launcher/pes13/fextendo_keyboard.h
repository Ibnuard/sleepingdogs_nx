/* LGPL-2.1-or-later. Bounded text ABI shared by Wine and the native applet. */
#ifndef FEXTENDO_KEYBOARD_H
#define FEXTENDO_KEYBOARD_H
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#ifdef FX_KEYBOARD_OVERLAY
#include "fextendo_osk.h"
#endif
#define FX_TEXT_UNITS 256
#define FX_TEXT_BYTES (FX_TEXT_UNITS * 4 + 1)
struct fx_text_request {
    uint64_t window;
    uint32_t thread, limit;
    uint16_t initial[FX_TEXT_UNITS + 1];
};
struct fx_text_result {
    int accepted;
    uint16_t text[FX_TEXT_UNITS + 1];
};

/* Reject malformed input and controls instead of partially injecting a string.
 * Capacity/limit are UTF-16 units; an astral character occupies two units. */
static inline int fx_text_decode(const char *src, size_t bytes, uint16_t *out, size_t limit) {
    size_t i=0,n=0;
    if(!src||!out||limit>FX_TEXT_UNITS)return -1;
    while(i<bytes&&src[i]){
        uint32_t c=(unsigned char)src[i++], min=0;unsigned extra=0;
        if(c<0x80){}
        else if(c>=0xc2&&c<=0xdf){c&=0x1f;extra=1;min=0x80;}
        else if(c>=0xe0&&c<=0xef){c&=0x0f;extra=2;min=0x800;}
        else if(c>=0xf0&&c<=0xf4){c&=7;extra=3;min=0x10000;}
        else return -1;
        while(extra--){if(i>=bytes)return -1;unsigned b=(unsigned char)src[i++];
            if((b&0xc0)!=0x80)return -1;c=(c<<6)|(b&63);}
        if(c<min||c>0x10ffff||(c>=0xd800&&c<=0xdfff)||c<32||c==127)return -1;
        if(n+(c>0xffff?2:1)>limit)return -1;
        if(c>0xffff){c-=0x10000;out[n++]=0xd800+(c>>10);out[n++]=0xdc00+(c&1023);}
        else out[n++]=(uint16_t)c;
    }
    if(i>=bytes)return -1;
    out[n]=0;return (int)n;
}
static inline int fx_text_encode(const uint16_t *src, char out[FX_TEXT_BYTES]) {
    size_t i=0,n=0;
    while(i<=FX_TEXT_UNITS&&src[i]){
        uint32_t c=src[i++];
        if(c>=0xd800&&c<=0xdbff){
            if(i>FX_TEXT_UNITS||src[i]<0xdc00||src[i]>0xdfff)return -1;
            c=0x10000+((c-0xd800)<<10)+(src[i++]-0xdc00);
        }else if(c>=0xdc00&&c<=0xdfff)return -1;
        if(c<32||c==127)return -1;
        if(c<0x80)out[n++]=(char)c;
        else if(c<0x800){out[n++]=0xc0|(c>>6);out[n++]=0x80|(c&63);}
        else if(c<0x10000){out[n++]=0xe0|(c>>12);out[n++]=0x80|((c>>6)&63);out[n++]=0x80|(c&63);}
        else{out[n++]=0xf0|(c>>18);out[n++]=0x80|((c>>12)&63);out[n++]=0x80|((c>>6)&63);out[n++]=0x80|(c&63);}
    }
    if(i>FX_TEXT_UNITS)return -1;
    out[n]=0;return (int)n;
}

uint64_t fx_keyboard_request(const struct fx_text_request *request);
int fx_keyboard_take(uint64_t token, struct fx_text_result *result);
void fx_keyboard_cancel(uint64_t token);
int fx_keyboard_manual(void);
unsigned fx_keyboard_manual_owner(void);
int fx_keyboard_input_blocked(void);
int fx_keyboard_delivering(void);
void fx_keyboard_delivery_done(void);
#endif
