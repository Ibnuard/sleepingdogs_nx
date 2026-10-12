/* SPDX-License-Identifier: LGPL-2.1-or-later. Based on PES13 startup checker UI. */
extern const unsigned char sd_boot_font[];
extern const unsigned sd_boot_font_size;
static int sd_boot_art_load(struct fx_art *a){
    memset(a,0,sizeof(*a));a->font_size=sd_boot_font_size;a->font=malloc(a->font_size);
    if(!a->font)return 0;memcpy(a->font,sd_boot_font,a->font_size);return 1;
}
static int fx_font_load(struct fx_art *a,const char *root){
    /* Same verified embedded font lets the keyboard open without SD I/O. */
    (void)root;return sd_boot_art_load(a);
}
static void sd_check_draw(struct fx_canvas *c,const struct fx_view *v){
    const struct sd_check_view *s=&v->check;
    static const char *const labels[]={"HOME launch mode","Low-memory patch","Game installation","Runtime files"};
    static const char *const phases[]={"Checking HOME launch mode","Testing low-window memory","Checking game installation","Verifying runtime files","Preparing launcher"};
    fx_rect(c,0,0,1280,720,FX_COLOR(3,10,20),255);
    fx_text(c,49,40,"SLEEPING DOGS  /  FEXTendo",1,FX_WHITE);
    fx_round(c,247,103,786,537,25,FX_COLOR(12,26,44),255);
    fx_text(c,290,130,s->failed?"Setup needs attention":"System Check",2,FX_WHITE);
    fx_text(c,291,188,"Checking your installation before you play.",0,FX_MUTED);
    for(int i=0;i<4;i++){
        int y=239+i*42;int failed=s->failed&&s->stage==i;
        fx_circle(c,302,y+13,9,s->done[i]?FX_COLOR(49,176,136):failed?FX_COLOR(224,100,90):FX_COLOR(46,65,85));
        fx_text(c,328,y,labels[i],0,FX_WHITE);
        const char *status=s->done[i]?(i==1?"Active / mapping passed":"Ready"):failed?"Required":s->stage==i?"Checking...":"Waiting";
        fx_text(c,714,y,status,0,s->done[i]?FX_MUTED:FX_BLUE);
    }
    if(s->failed){
        fx_wrapped(c,291,420,s->error,696);
        fx_text(c,291,582,"A  Retry checks",0,FX_WHITE);fx_text(c,705,582,"B / +  Close",0,FX_MUTED);
    }else{
        fx_text(c,291,438,phases[s->stage],0,FX_WHITE);
        if(s->percent>=0){char text[12];snprintf(text,sizeof(text),"%d%%",s->percent);fx_text(c,931,438,text,0,FX_BLUE);}
        fx_round(c,291,487,698,5,2,FX_COLOR(35,55,77),255);
        int w=s->percent>=0?s->percent*698/100:140;
        int x=s->percent>=0?291:291+(int)(v->frame%160<80?v->frame%160:160-v->frame%160)*6;
        if(w)fx_round(c,x,487,w,5,2,FX_BLUE,255);
        fx_text(c,291,545,"Low-memory patch must be active on this boot.",0,FX_MUTED);
        fx_text(c,291,582,"B / +  Close",0,FX_MUTED);
    }
    fx_text(c,49,669,"Sleeping Dogs  /  " FX_APP_VERSION,0,FX_MUTED);
}
