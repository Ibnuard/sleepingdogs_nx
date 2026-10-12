/* Run the actual native overlay queue and Wine pump against an editable game
 * field model. Only OS/controller/display/window services are substituted. */
#define FX_KEYBOARD_OVERLAY 1
#define FX_TEST_LIVE_KEYS 1
static void fx_test_live_key(unsigned vk,unsigned flags);
#define main fx_native_regression_main
#include "fextendo_keyboard.c"
#undef main
static int display_open,display_fail,display_wait,display_draws,touch_on,touch_x,touch_y;
static int fx_osk_display_show(const struct fx_osk_core *s,unsigned p,int single){
    (void)s;(void)single;assert(p<2);if(display_fail)return 0;display_open=1;display_draws++;return display_wait?2:1;
}
static void fx_osk_display_close(void){display_open=0;}
static int fx_osk_touch(int *x,int *y){*x=touch_x;*y=touch_y;return touch_on;}
#include "fextendo_osk_switch.h"
static char field[257];static size_t cursor;static int enters;
static void fx_test_live_key(unsigned vk,unsigned flags){
    if(flags&KEYEVENTF_KEYUP)return;
    size_t len=strlen(field);
    if(vk==8&&cursor){memmove(field+cursor-1,field+cursor,len-cursor+1);cursor--;}
    else if(vk==0x2e&&cursor<len)memmove(field+cursor,field+cursor+1,len-cursor);
    else if(vk==0x25&&cursor)cursor--;
    else if(vk==0x27&&cursor<len)cursor++;
    else if(vk==0x24)cursor=0;
    else if(vk==0x23)cursor=len;
    else if(vk==13)enters++;
    else if((vk>='A'&&vk<='Z')||vk==32){
        assert(len<256);memmove(field+cursor+1,field+cursor,len-cursor+1);
        field[cursor++]=vk+((vk>='A'&&vk<='Z'&&!(keyboard_state[VK_SHIFT]&0x80))?32:0);
    }
}
static void fresh(void){
    reset();edit_class=0;fx_osk_display_close();
    memset(&fx_osk_state,0,sizeof(fx_osk_state));fx_osk_phase=FX_OSK_IDLE;fx_osk_blocking=fx_osk_unclaimed=0;
    display_fail=display_wait=display_draws=touch_on=enters=0;fx_keyboard_manual_player=0;
    strcpy(field,"Nunu");cursor=4;
}
static void step(void){ticks+=20;fx_osk_service();pump();}
static void open_keyboard(unsigned player){
    fx_keyboard_manual_player=player;fx_keyboard_manual_pending=1;pump();
    assert(fx_wine_text.overlay&&fx_osk_phase==FX_OSK_PENDING&&!fx_wine_text.token);
    step();step();assert(display_open&&fx_osk_state.armed&&fx_osk_player==player&&!opens);
}
static void press(unsigned player,uint64_t b){fx_samples[player].buttons=b;step();fx_samples[player].buttons=0;step();}
static void key(unsigned character,unsigned vk){assert(fx_osk_enqueue(&fx_osk_state,(struct fx_osk_key){character,vk}));}
static void finish_keys(void){
    for(unsigned n=0;n<256&&(fx_osk_state.count||fx_wine_text.overlay_stage);n++)step();
    assert(!fx_osk_state.count&&!fx_wine_text.down&&!fx_wine_text.shift);
}
static void close_keyboard(void){
    fx_osk_activate(&fx_osk_state,FX_OSK_CELLS-1);
    for(unsigned n=0;n<256&&fx_osk_blocked();n++)step();
    assert(!fx_osk_blocked()&&!display_open&&!fx_wine_text.overlay);
    for(unsigned i=0;i<256;i++)assert(!(keyboard_state[i]&0x80));
}
#ifndef FX_TEST_OSK_MAIN
#define FX_TEST_OSK_MAIN main
#endif
int FX_TEST_OSK_MAIN(void){
    /* A published texture is not permission to type: wait for real Present. */
    fresh();display_wait=1;assert(fx_osk_open(0));
    fx_osk_service();pump();assert(fx_osk_phase==FX_OSK_PENDING);
    press(0,FX_PAD_A);assert(!event_count&&!fx_osk_state.count&&!strcmp(field,"Nunu"));
    display_wait=0;step();step();assert(fx_osk_phase==FX_OSK_OPEN);close_keyboard();
    fresh();display_wait=1;assert(fx_osk_open(0));fx_osk_service();pump();
    display_fail=1;fx_osk_service();assert(fx_osk_phase==FX_OSK_DRAIN);
    fx_osk_service();assert(!fx_osk_blocked()&&!event_count); /* no present + no Wine pump */
    fresh();open_keyboard(0);
    for(int i=0;i<4;i++)press(0,FX_PAD_B);
    key('B',0);key('e',0);key('j',0);key('o',0);close_keyboard();
    assert(!strcmp(field,"Bejo")&&!enters); /* closes only after queued edits finish */
    assert(!fx_osk_open(1));open_keyboard(0);assert(!strcmp(field,"Bejo"));
    press(1,FX_PAD_B);assert(!fx_osk_state.count&&!strcmp(field,"Bejo")); /* P2 cannot drive P1 keyboard */
    press(0,FX_PAD_L);press(0,FX_PAD_L);key(0,0x2e);key('J',0);finish_keys();
    assert(!strcmp(field,"BeJo"));
    press(0,FX_PAD_PLUS);finish_keys();assert(enters==1);close_keyboard();
    fresh();open_keyboard(0);key(0,0x24);key(0,0x2e);key('B',0);key(0,0x23);finish_keys();
    assert(!strcmp(field,"Bunu")&&cursor==4);close_keyboard();
    /* A held opening chord must not type, move the caret or repeat. */
    fresh();fx_samples[0].buttons=FX_PAD_L|FX_PAD_R|FX_PAD_LSTICK;fx_keyboard_poll_locked();pump();
    ticks+=600;fx_keyboard_poll_locked();pump();
    for(int i=0;i<8;i++)step();assert(!fx_osk_state.armed&&!event_count);
    fx_samples[0].buttons=0;step();assert(fx_osk_state.armed);close_keyboard();
    /* Focus loss, destruction, native focus loss and disconnect release Shift
     * and the current key, drop queued edits, and retain controller suppression
     * until neutral. No background typing or stuck key survives. */
    for(int reason=0;reason<4;reason++){
        fresh();open_keyboard(0);key('H',0);key('i',0);step();step();
        assert(fx_wine_text.shift&&fx_wine_text.down);
        if(reason==0)focus=foreground=11;
        if(reason==1)wine_nx_drv_DestroyWindow(focus);
        if(reason==2)focus_state=0;
        if(reason==3)game_paused=1;
        step();assert(!fx_wine_text.overlay&&!fx_wine_text.down&&!fx_wine_text.shift&&!fx_osk_state.count);
        assert(!strcmp(field,"NunuH"));focus_state=1;game_paused=0;step();
        assert(!display_open&&!fx_osk_blocked());
    }
    fresh();open_keyboard(0);uint64_t old=fx_wine_text.overlay;close_keyboard();open_keyboard(0);
    fx_osk_abort(old);fx_osk_finished(old);assert(fx_osk_valid(fx_wine_text.overlay));close_keyboard();
    fresh();display_fail=1;fx_keyboard_manual_pending=1;pump();step();step();
    assert(!fx_wine_text.overlay&&!fx_osk_blocked()&&!event_count); /* safe presentation failure */
    /* A game may stop pumping window events after claiming the shortcut.
     * Failure before the first frame must still restore P1 natively. */
    fresh();display_fail=1;fx_keyboard_manual_pending=1;pump();
    uint64_t failed_token=fx_wine_text.overlay;assert(failed_token&&!fx_osk_unclaimed);
    fx_osk_service();assert(fx_osk_phase==FX_OSK_DRAIN);
    fx_samples[0].buttons=FX_PAD_PLUS;fx_osk_service();assert(fx_osk_blocked());
    fx_samples[0].buttons=0;fx_samples[1].buttons=FX_PAD_A;fx_osk_service();
    assert(!fx_osk_blocked()&&!event_count); /* no Wine pump and P2 held */
    display_fail=0;uint64_t next_token=fx_osk_open(0);assert(next_token&&next_token!=failed_token);
    fx_osk_finished(failed_token);fx_osk_display_failed(failed_token);assert(fx_osk_valid(next_token));
    fresh();
    fresh();open_keyboard(0);assert(!fx_keyboard_request(&(struct fx_text_request){.window=10,.thread=1,.limit=32}));
    close_keyboard();edit_class=1;pump();assert(fx_wine_text.token&&!fx_wine_text.overlay);
    fx_keyboard_service();pump();assert(replacements==1&&opens==1); /* standard Edit retains native prefill */
    fresh();open_keyboard(0);fx_osk_activate(&fx_osk_state,FX_OSK_CELLS-1);fx_samples[1].buttons=FX_PAD_A;
    step();step();assert(!fx_osk_blocked()&&!display_open);
    fx_samples[1].buttons=0;step();assert(!fx_osk_blocked());
    /* Touch positions follow top/bottom placement, and holding a touch does
     * not repeat letters. Moving by Y is usable on every normalized pad. */
    fresh();open_keyboard(0);touch_on=1;touch_x=40;touch_y=720-FX_OSK_HEIGHT+FX_OSK_KEY_TOP+2*FX_OSK_ROW_STEP+10;
    step();step();touch_on=0;finish_keys();assert(!strcmp(field,"Nunua"));
    press(0,FX_PAD_Y);assert(fx_osk_state.top);touch_on=1;touch_y=FX_OSK_KEY_TOP+2*FX_OSK_ROW_STEP+10;
    step();touch_on=0;finish_keys();assert(!strcmp(field,"Nunuaa"));close_keyboard();
    fresh();fx_keyboard_options.top=1;open_keyboard(0);assert(fx_osk_state.top);close_keyboard();
    struct fx_osk_core s={.armed=1};struct fx_pad_sample pad={.connected=1};
    for(int i=0;i<FX_OSK_QUEUE;i++)assert(fx_osk_enqueue(&s,(struct fx_osk_key){'a',0}));
    assert(!fx_osk_enqueue(&s,(struct fx_osk_key){'b',0})&&s.full&&s.count==FX_OSK_QUEUE);
    struct fx_osk_key k;assert(fx_osk_dequeue(&s,&k)&&k.character=='a'&&!s.full);
    memset(&s,0,sizeof(s));s.armed=1;pad.buttons=FX_PAD_B;
    fx_osk_input(&s,&pad,0,0,0,0,0);fx_osk_input(&s,&pad,0,0,0,0,349);assert(s.count==1);
    fx_osk_input(&s,&pad,0,0,0,0,350);assert(s.count==2);
    for(int kind=FX_PAD_LEFT;kind<=FX_PAD_RIGHT;kind++){
        memset(&s,0,sizeof(s));s.armed=1;s.selected=24;
        pad=fx_pad_normalize(kind,1,0,0,kind==FX_PAD_LEFT?-24000:0,0,kind==FX_PAD_RIGHT?24000:0);
        fx_osk_input(&s,&pad,0,0,0,0,0);assert(s.selected==25);
        pad=fx_pad_normalize(kind,1,kind==FX_PAD_LEFT?FX_PAD_DOWN:FX_PAD_X,0,0,0,0);
        fx_osk_input(&s,&pad,0,0,0,0,20);assert(s.count==1&&s.queue[0].character=='s');
    }
    puts("PASS: live Nunu -> Bejo, middle edits, Enter/close, focus/reconnect release, P1/P2 ownership, native Edit, touch, queue/repeat, horizontal controls");
    return 0;
}
