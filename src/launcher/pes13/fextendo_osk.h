/* LGPL-2.1-or-later. Live keyboard editing, inspired by Autorun's OSK
 * (autorunhq/autorun c889e4e). This implementation uses FEXTendo's normalized
 * controllers, font and independent VI layer; it does not read game memory. */
#ifndef FEXTENDO_OSK_H
#define FEXTENDO_OSK_H
#include <stdint.h>
#include <string.h>
#include "fextendo_gamepad.h"
#define FX_OSK_HEIGHT 252
#define FX_OSK_KEY_TOP 8
#define FX_OSK_KEY_HEIGHT 36
#define FX_OSK_ROW_STEP 40
#define FX_OSK_QUEUE 32
struct fx_osk_key { uint16_t character, vk; };
enum { FX_OSK_SHIFT=1, FX_OSK_MOVE, FX_OSK_CLOSE };
struct fx_osk_cell { const char *label; uint16_t character,vk; unsigned char action,width; };
#define FX_OK(c) {NULL,c,0,0,1}
#define FX_OV(s,v) {s,0,v,0,1}
static const struct fx_osk_cell fx_osk_cells[] = {
    FX_OK('1'),FX_OK('2'),FX_OK('3'),FX_OK('4'),FX_OK('5'),FX_OK('6'),FX_OK('7'),FX_OK('8'),FX_OK('9'),FX_OK('0'),FX_OK('-'),FX_OK('='),
    FX_OK('q'),FX_OK('w'),FX_OK('e'),FX_OK('r'),FX_OK('t'),FX_OK('y'),FX_OK('u'),FX_OK('i'),FX_OK('o'),FX_OK('p'),FX_OK('['),FX_OK(']'),
    FX_OK('a'),FX_OK('s'),FX_OK('d'),FX_OK('f'),FX_OK('g'),FX_OK('h'),FX_OK('j'),FX_OK('k'),FX_OK('l'),FX_OK(';'),FX_OK('\''),FX_OK('\\'),
    {"Shift",0,0,FX_OSK_SHIFT,1},FX_OK('z'),FX_OK('x'),FX_OK('c'),FX_OK('v'),FX_OK('b'),FX_OK('n'),FX_OK('m'),FX_OK(','),FX_OK('.'),FX_OK('/'),FX_OV("Backspace",0x08),
    {"Space",' ',0,0,2},FX_OV("Delete",0x2e),FX_OV("Left",0x25),FX_OV("Right",0x27),FX_OV("Home",0x24),FX_OV("End",0x23),FX_OV("Up",0x26),FX_OV("Down",0x28),
    {"Move",0,0,FX_OSK_MOVE,1},FX_OV("Enter",0x0d),{"Close",0,0,FX_OSK_CLOSE,1}
};
#undef FX_OK
#undef FX_OV
#define FX_OSK_CELLS ((int)(sizeof(fx_osk_cells)/sizeof(*fx_osk_cells)))
struct fx_osk_core {
    struct fx_osk_key queue[FX_OSK_QUEUE];
    unsigned head,count,generation;
    int selected,shift,top,closing,armed,touched,full;
    uint64_t previous,repeat_at;
};
static unsigned fx_osk_character(unsigned c,int shift) {
    if(!shift)return c;
    if(c>='a'&&c<='z')return c-'a'+'A';
    const char *plain="1234567890-=[];'\\,./",*upper="!@#$%^&*()_+{}:\"|<>?";
    for(unsigned i=0;plain[i];i++)if(c==(unsigned char)plain[i])return (unsigned char)upper[i];
    return c;
}
static int fx_osk_enqueue(struct fx_osk_core *s,struct fx_osk_key key) {
    if(s->closing)return 0;
    if(s->count==FX_OSK_QUEUE){if(!s->full){s->full=1;s->generation++;}return 0;}
    s->queue[(s->head+s->count)%FX_OSK_QUEUE]=key;s->count++;s->full=0;s->generation++;return 1;
}
static int fx_osk_dequeue(struct fx_osk_core *s,struct fx_osk_key *key) {
    if(!s->count)return 0;
    *key=s->queue[s->head];s->head=(s->head+1)%FX_OSK_QUEUE;s->count--;s->full=0;s->generation++;return 1;
}
static void fx_osk_activate(struct fx_osk_core *s,int index) {
    if(index<0||index>=FX_OSK_CELLS||s->closing)return;
    const struct fx_osk_cell *cell=&fx_osk_cells[index];
    if(cell->action==FX_OSK_SHIFT){s->shift=!s->shift;s->generation++;}
    else if(cell->action==FX_OSK_MOVE){s->top=!s->top;s->generation++;}
    else if(cell->action==FX_OSK_CLOSE){s->closing=1;s->generation++;}
    else if(fx_osk_enqueue(s,(struct fx_osk_key){fx_osk_character(cell->character,s->shift),cell->vk})&&cell->character&&s->shift){s->shift=0;s->generation++;}
}
static void fx_osk_bounds(int index,int *x,int *y,int *width) {
    int row=index/12,col=index%12;
    if(row==4&&col)col++;
    *x=28+col*102;*y=FX_OSK_KEY_TOP+row*FX_OSK_ROW_STEP;*width=fx_osk_cells[index].width*102-6;
}
static int fx_osk_hit(int x,int y) {
    for(int i=0;i<FX_OSK_CELLS;i++){
        int left,top,width;fx_osk_bounds(i,&left,&top,&width);
        if(x>=left&&x<left+width&&y>=top&&y<top+FX_OSK_KEY_HEIGHT)return i;
    }
    return -1;
}
static void fx_osk_move(struct fx_osk_core *s,int dx,int dy) {
    int old=s->selected,row=old/12,col=old%12;
    if(dx){int n=row==4?11:12;col=(col+dx+n)%n;}
    if(dy){row=(row+dy+5)%5;if(row==4&&col>10)col=10;}
    s->selected=row*12+col;if(old!=s->selected)s->generation++;
}
/* The caller owns serialization. All inputs are normalized, including a
 * horizontal single Joy-Con's face buttons, stick and SL/SR shoulders. */
static void fx_osk_input(struct fx_osk_core *s,const struct fx_pad_sample *p,
                         int neutral,int touching,int x,int y,uint64_t now_ms) {
    uint64_t held=p->buttons;
    if(p->lx>16000)held|=FX_PAD_RIGHT_BUTTON;
    if(p->lx<-16000)held|=FX_PAD_LEFT_BUTTON;
    if(p->ly>16000)held|=FX_PAD_UP;
    if(p->ly<-16000)held|=FX_PAD_DOWN;
    if(!s->armed){s->previous=held;s->touched=touching;if(neutral&&!touching){s->armed=1;s->previous=0;s->generation++;}return;}
    if(s->closing)return;
    uint64_t down=held&~s->previous;
    const uint64_t repeat=FX_PAD_UP|FX_PAD_DOWN|FX_PAD_LEFT_BUTTON|FX_PAD_RIGHT_BUTTON|FX_PAD_B|FX_PAD_L|FX_PAD_R;
    if((held&repeat)!=(s->previous&repeat))s->repeat_at=now_ms+350;
    else if((held&repeat)&&now_ms>=s->repeat_at){down|=held&repeat;s->repeat_at=now_ms+100;}
    s->previous=held;
    if(down&FX_PAD_MINUS){s->closing=1;s->generation++;return;}
    if(down&FX_PAD_Y){s->top=!s->top;s->generation++;}
    if(down&FX_PAD_X){s->shift=!s->shift;s->generation++;}
    if(down&FX_PAD_UP)fx_osk_move(s,0,-1);
    else if(down&FX_PAD_DOWN)fx_osk_move(s,0,1);
    else if(down&FX_PAD_LEFT_BUTTON)fx_osk_move(s,-1,0);
    else if(down&FX_PAD_RIGHT_BUTTON)fx_osk_move(s,1,0);
    if(down&FX_PAD_B)fx_osk_enqueue(s,(struct fx_osk_key){0,0x08});
    else if(down&FX_PAD_L)fx_osk_enqueue(s,(struct fx_osk_key){0,0x25});
    else if(down&FX_PAD_R)fx_osk_enqueue(s,(struct fx_osk_key){0,0x27});
    else if(down&FX_PAD_PLUS)fx_osk_enqueue(s,(struct fx_osk_key){0,0x0d});
    else if(down&FX_PAD_A)fx_osk_activate(s,s->selected);
    if(touching&&!s->touched){int hit=fx_osk_hit(x,y);if(hit>=0){s->selected=hit;s->generation++;fx_osk_activate(s,hit);}}
    s->touched=touching;
}
uint64_t fx_osk_open(unsigned player);
uint64_t fx_osk_claim(void);
int fx_osk_blocked(void);
int fx_osk_valid(uint64_t token);
int fx_osk_next(uint64_t token,struct fx_osk_key *key);
void fx_osk_abort(uint64_t token);
void fx_osk_finished(uint64_t token);
#endif
