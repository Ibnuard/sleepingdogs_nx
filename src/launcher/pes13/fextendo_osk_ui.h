/* LGPL-2.1-or-later. Draw the compact keyboard into native RGBA pixels. */
#include "fextendo_osk_sprites.h"
static void fx_osk_icon(struct fx_canvas *c,int x,int y,int id) {
    fx_image(c,fx_osk_sprites[id],40,40,x,y,32,32,0,255);
}
static void fx_osk_hint(struct fx_canvas *c,int x,int id,const char *label) {
    fx_osk_icon(c,x,212,id);fx_text(c,x+38,217,label,0,FX_WHITE);
}
static void fx_osk_draw(struct fx_canvas *c,const struct fx_osk_core *s,unsigned player,int single) {
    (void)player;
    fx_rect(c,0,0,FX_W,FX_OSK_HEIGHT,FX_COLOR(8,20,34),255);
    fx_rect(c,0,0,FX_W,2,FX_BLUE,255);
    for(int i=0;i<FX_OSK_CELLS;i++){
        const struct fx_osk_cell *key=&fx_osk_cells[i];char character[2]={0};
        int x,y,w;fx_osk_bounds(i,&x,&y,&w);
        int selected=i==s->selected,shift=key->action==FX_OSK_SHIFT&&s->shift;
        fx_round(c,x,y,w,FX_OSK_KEY_HEIGHT,8,selected?FX_BLUE:shift?FX_COLOR(34,89,117):FX_COLOR(24,42,61),255);
        const char *label=key->label;
        if(!label){character[0]=fx_osk_character(key->character,s->shift);label=character;}
        fx_center(c,x+w/2,y+7,label,strlen(label)>7?3:0,selected?FX_COLOR(5,18,30):FX_WHITE);
    }
    fx_osk_hint(c,28,FX_OSK_SPRITE_A,"Select");fx_osk_hint(c,177,FX_OSK_SPRITE_B,"Backspace");
    fx_osk_hint(c,389,FX_OSK_SPRITE_X,"Shift");fx_osk_hint(c,535,FX_OSK_SPRITE_Y,"Move");
    fx_osk_icon(c,681,212,single?FX_OSK_SPRITE_SL:FX_OSK_SPRITE_L);
    fx_osk_icon(c,717,212,single?FX_OSK_SPRITE_SR:FX_OSK_SPRITE_R);
    fx_text(c,755,217,"Cursor",0,FX_WHITE);
    fx_osk_hint(c,904,single==1?FX_OSK_SPRITE_MINUS:FX_OSK_SPRITE_PLUS,"Enter");
    if(!single)fx_osk_hint(c,1090,FX_OSK_SPRITE_MINUS,"Close");
}
