/* LGPL-2.1-or-later. Shared, platform-independent controller normalization. */
#ifndef FEXTENDO_GAMEPAD_H
#define FEXTENDO_GAMEPAD_H
#include <stdint.h>
#include <string.h>

enum fx_pad_kind { FX_PAD_FULL, FX_PAD_LEFT, FX_PAD_RIGHT, FX_PAD_DUAL, FX_PAD_HANDHELD };
#define FX_PAD_BIT(n) (UINT64_C(1) << (n))
#define FX_PAD_A FX_PAD_BIT(0)
#define FX_PAD_B FX_PAD_BIT(1)
#define FX_PAD_X FX_PAD_BIT(2)
#define FX_PAD_Y FX_PAD_BIT(3)
#define FX_PAD_LSTICK FX_PAD_BIT(4)
#define FX_PAD_RSTICK FX_PAD_BIT(5)
#define FX_PAD_L FX_PAD_BIT(6)
#define FX_PAD_R FX_PAD_BIT(7)
#define FX_PAD_ZL FX_PAD_BIT(8)
#define FX_PAD_ZR FX_PAD_BIT(9)
#define FX_PAD_PLUS FX_PAD_BIT(10)
#define FX_PAD_MINUS FX_PAD_BIT(11)
#define FX_PAD_LEFT_BUTTON FX_PAD_BIT(12)
#define FX_PAD_UP FX_PAD_BIT(13)
#define FX_PAD_RIGHT_BUTTON FX_PAD_BIT(14)
#define FX_PAD_DOWN FX_PAD_BIT(15)
#define FX_PAD_SL (FX_PAD_BIT(24) | FX_PAD_BIT(26))
#define FX_PAD_SR (FX_PAD_BIT(25) | FX_PAD_BIT(27))

struct fx_pad_sample {
    uint64_t buttons;
    int32_t lx, ly, rx, ry;
    uint32_t packet;
    int connected, kind;
};

static inline int32_t fx_pad_axis(int64_t n) {
    return n > 32767 ? 32767 : n < -32768 ? -32768 : (int32_t)n;
}

static inline struct fx_pad_sample fx_pad_normalize(int kind, int connected, uint64_t raw,
                                                   int32_t lx, int32_t ly, int32_t rx, int32_t ry) {
    struct fx_pad_sample out={0};
    out.kind=kind;out.connected=!!connected;
    if(!connected)return out;
    if(kind!=FX_PAD_LEFT&&kind!=FX_PAD_RIGHT){
        out.buttons=raw;out.lx=fx_pad_axis(lx);out.ly=fx_pad_axis(ly);
        out.rx=fx_pad_axis(rx);out.ry=fx_pad_axis(ry);return out;
    }
    if(kind==FX_PAD_LEFT){
        if(raw&FX_PAD_DOWN)out.buttons|=FX_PAD_A;
        if(raw&FX_PAD_LEFT_BUTTON)out.buttons|=FX_PAD_B;
        if(raw&FX_PAD_UP)out.buttons|=FX_PAD_Y;
        if(raw&FX_PAD_RIGHT_BUTTON)out.buttons|=FX_PAD_X;
        out.lx=fx_pad_axis(-(int64_t)ly);out.ly=fx_pad_axis(lx);
    }else{
        if(raw&FX_PAD_X)out.buttons|=FX_PAD_A;
        if(raw&FX_PAD_A)out.buttons|=FX_PAD_B;
        if(raw&FX_PAD_B)out.buttons|=FX_PAD_Y;
        if(raw&FX_PAD_Y)out.buttons|=FX_PAD_X;
        out.lx=fx_pad_axis(ry);out.ly=fx_pad_axis(-(int64_t)rx);
    }
    if(raw&FX_PAD_SL)out.buttons|=FX_PAD_L;
    if(raw&FX_PAD_SR)out.buttons|=FX_PAD_R;
    if(raw&(FX_PAD_PLUS|FX_PAD_MINUS))out.buttons|=FX_PAD_PLUS;
    if(raw&(FX_PAD_LSTICK|FX_PAD_RSTICK))out.buttons|=FX_PAD_LSTICK;
    /* No D-pad, ZL/ZR, second stick or stale portrait stick-direction bits. */
    return out;
}

static inline uint64_t fx_pad_navigation(const struct fx_pad_sample *p) {
    uint64_t b=p->buttons;
    if(p->lx < -12000)b|=FX_PAD_LEFT_BUTTON;
    if(p->lx > 12000)b|=FX_PAD_RIGHT_BUTTON;
    if(p->ly > 12000)b|=FX_PAD_UP;
    if(p->ly < -12000)b|=FX_PAD_DOWN;
    return b;
}

static inline int fx_pad_neutral(const struct fx_pad_sample *p) {
    return !(p->buttons&UINT64_C(0x0f00ffff)) &&
        p->lx>=-8000&&p->lx<=8000&&p->ly>=-8000&&p->ly<=8000&&
        p->rx>=-8000&&p->rx<=8000&&p->ry>=-8000&&p->ry<=8000;
}

static inline void fx_pad_update(struct fx_pad_sample *previous, struct fx_pad_sample next) {
    next.packet=previous->packet;
    if(next.buttons!=previous->buttons||next.lx!=previous->lx||next.ly!=previous->ly||
       next.rx!=previous->rx||next.ry!=previous->ry||next.connected!=previous->connected||next.kind!=previous->kind)
        next.packet++;
    *previous=next;
}

enum fx_reconnect_phase { FX_RECONNECT_RUNNING, FX_RECONNECT_APPLET, FX_RECONNECT_NEUTRAL,
                          FX_RECONNECT_WAIT, FX_RECONNECT_DRAIN };
struct fx_reconnect { enum fx_reconnect_phase phase; unsigned required; };

static inline int fx_reconnect_poll(struct fx_reconnect *r,unsigned connected,int neutral,int resume) {
    int complete=(connected&r->required)==r->required;
    if(r->phase==FX_RECONNECT_RUNNING&&!complete){r->phase=FX_RECONNECT_APPLET;return 1;}
    if(r->phase==FX_RECONNECT_NEUTRAL&&neutral)r->phase=FX_RECONNECT_WAIT;
    else if(r->phase==FX_RECONNECT_WAIT&&complete&&resume)r->phase=FX_RECONNECT_DRAIN;
    else if(r->phase==FX_RECONNECT_DRAIN){
        if(!complete)r->phase=FX_RECONNECT_NEUTRAL;
        else if(neutral)r->phase=FX_RECONNECT_RUNNING;
    }
    return 0;
}

/* libnx implementation shared by launcher, XInput and pointer fallback. */
void fx_pads_init(void);
void fx_pads_snapshot(struct fx_pad_sample out[2]);
unsigned fx_pads_players(void);
int fx_pads_capture_session(void);
int fx_pads_ready(void);
int fx_pads_connect(void);
int fx_pads_begin_game(void);
int fx_pads_paused(void);
void wine_nx_gamepad_wait(void);
int fx_pads_game_state(unsigned index,struct fx_pad_sample *out);
#endif
