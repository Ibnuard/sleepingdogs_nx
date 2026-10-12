/* Execute the actual native queue, Wine detector/delivery and Horizon key
 * encoder. Only platform applet, window APIs and HID are simulated. */
#include <assert.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "fextendo_gamepad.h"
#include "fextendo_keyboard.h"
#include "horizon_keyboard.h"

typedef uint32_t Result;
typedef struct { unsigned limit; char initial[FX_TEXT_BYTES]; } SwkbdConfig;
typedef enum { SwkbdTextCheckResult_OK,SwkbdTextCheckResult_Bad } SwkbdTextCheckResult;
static SwkbdTextCheckResult (*validator)(char *,size_t);
#define R_SUCCEEDED(rc) (!(rc))
#define R_FAILED(rc) (!!(rc))
#define AppletFocusState_InFocus 1
#define AppletFocusHandlingMode_SuspendHomeSleep 0
#define AppletFocusHandlingMode_AlwaysSuspend 3
static int game_paused,fx_game_active=1,fx_keyboard_ready=1,opens,closes,show_cancel,show_disconnect,show_hold;
static int fx_keyboard_applet_active,focus_mode=3,focus_changes,focus_fail,restore_fail,show_calls;
static int focus_state=AppletFocusState_InFocus;
static unsigned fx_players=2;
static uint64_t ticks=1;
static struct fx_pad_sample fx_samples[2];
static pthread_mutex_t fx_pad_applet_lock=PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t fx_pad_lock=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t fx_pad_cond=PTHREAD_COND_INITIALIZER;
static const char *typed="New Save";
static char last_initial[FX_TEXT_BYTES];
static unsigned last_limit;
int fx_pads_paused(void){return game_paused;}
static uint64_t armGetSystemTick(void){return ticks;}
static uint64_t armGetSystemTickFreq(void){return 1000;}
unsigned fx_pads_players(void){return fx_players;}
static int appletGetFocusState(void){return focus_state;}
static Result appletSetFocusHandlingMode(int mode){
    assert(fx_keyboard_applet_active);focus_changes++;
    if((mode==0&&focus_fail)||(mode==3&&restore_fail))return 1;
    focus_mode=mode;return 0;
}
void fx_pads_snapshot(struct fx_pad_sample out[2]){memcpy(out,fx_samples,sizeof(fx_samples));}
static Result swkbdCreate(SwkbdConfig *c,int words){assert(!words);memset(c,0,sizeof(*c));opens++;return 0;}
static void swkbdClose(SwkbdConfig *c){(void)c;closes++;}
static void swkbdConfigMakePresetDefault(SwkbdConfig *c){(void)c;}
static void swkbdConfigSetHeaderText(SwkbdConfig *c,const char *s){(void)c;(void)s;}
static void swkbdConfigSetGuideText(SwkbdConfig *c,const char *s){(void)c;(void)s;}
static void swkbdConfigSetReturnButtonFlag(SwkbdConfig *c,int flag){(void)c;assert(!flag);}
static void swkbdConfigSetStringLenMin(SwkbdConfig *c,unsigned n){(void)c;assert(!n);}
static void swkbdConfigSetStringLenMax(SwkbdConfig *c,unsigned n){c->limit=n;}
static void swkbdConfigSetInitialText(SwkbdConfig *c,const char *s){strcpy(c->initial,s);}
static void swkbdConfigSetTextCheckCallback(SwkbdConfig *c,SwkbdTextCheckResult (*cb)(char *,size_t)){(void)c;validator=cb;}
static Result swkbdShow(SwkbdConfig *c,char *out,size_t n){
    show_calls++;
    /* Plus/Enter needs the caller to run its TextCheck callback. */
    assert(focus_mode==AppletFocusHandlingMode_SuspendHomeSleep&&fx_keyboard_applet_active);
    /* No controller mutex and no second applet may be active. */
    assert(pthread_mutex_trylock(&fx_pad_applet_lock)!=0);
    strcpy(last_initial,c->initial);last_limit=c->limit;
    assert(strlen(typed)<n);strcpy(out,typed);
    if(show_disconnect)game_paused=1;
    if(show_hold)fx_samples[1].buttons=FX_PAD_A;
    return show_cancel?1:validator(out,n)!=SwkbdTextCheckResult_OK;
}
#include "fextendo_keyboard_switch.h"

typedef uintptr_t HWND;
typedef uint16_t WCHAR;
typedef uint32_t UINT,DWORD;
typedef uint16_t WORD;
typedef intptr_t LRESULT,LPARAM;
typedef uintptr_t WPARAM;
typedef int BOOL;
typedef struct { unsigned short Length,MaximumLength;WCHAR *Buffer; } UNICODE_STRING;
typedef struct { int left,top,right,bottom; } RECT;
typedef struct { DWORD cbSize;HWND hwndCaret; } GUITHREADINFO;
typedef struct { DWORD type;struct { uint16_t wVk,wScan;DWORD dwFlags; } ki; } INPUT;
#define FALSE 0
#define TRUE 1
#define GA_ROOT 2
#define GWL_STYLE -16
#define ES_READONLY 0x800
#define ES_PASSWORD 0x20
#define ES_MULTILINE 4
#define WM_GETTEXT 0xd
#define WM_GETTEXTLENGTH 0xe
#define EM_GETLIMITTEXT 0xd5
#define EM_SETSEL 0xb1
#define EM_REPLACESEL 0xc2
#define INPUT_KEYBOARD 1
#define KEYEVENTF_UNICODE 4
#define KEYEVENTF_KEYUP 2
#define KEYEVENTF_EXTENDEDKEY 1
#define MAPVK_VK_TO_VSC_EX 4
#define VK_SHIFT 0x10
static HWND focus=10,foreground=10,caret;
static unsigned current_tid=1,owner_tid=1,style,edit_limit=32;
static int edit_class=1,visible=1,enabled=1,replacements,selections;
static WCHAR edit_text[FX_TEXT_UNITS+1];
static INPUT events[FX_TEXT_UNITS*4];
static size_t event_count;
static unsigned char keyboard_state[256];
static char inserted[FX_TEXT_UNITS+1];
static unsigned inserted_count;
static DWORD milliseconds=100;
static HWND get_focus(void){return focus;}
static HWND NtUserGetForegroundWindow(void){return foreground;}
static DWORD GetCurrentThreadId(void){return current_tid;}
static DWORD get_window_thread(HWND w,DWORD *p){(void)w;(void)p;return owner_tid;}
static BOOL is_window_visible(HWND w){(void)w;return visible;}
static BOOL is_window_enabled(HWND w){(void)w;return enabled;}
static HWND NtUserGetAncestor(HWND w,int type){assert(type==GA_ROOT);return w;}
static int NtUserGetClassName(HWND w,BOOL real,UNICODE_STRING *s){
    (void)w;assert(!real);
    const WCHAR name[]={'E','d','i','t',0};
    if(!edit_class)return 0;
    memcpy(s->Buffer,name,sizeof(name));return 4;
}
static unsigned NtUserGetWindowLongW(HWND w,int index){(void)w;assert(index==GWL_STYLE);return style;}
static BOOL NtUserGetGUIThreadInfo(DWORD tid,GUITHREADINFO *i){assert(tid==current_tid);i->hwndCaret=caret;return 1;}
static DWORD NtGetTickCount(void){return milliseconds;}
static uintptr_t NtUserGetKeyboardLayout(unsigned tid){assert(!tid);return 1;}
static unsigned NtUserMapVirtualKeyEx(unsigned vk,unsigned type,uintptr_t layout){
    assert(type==MAPVK_VK_TO_VSC_EX&&layout==1);return vk==VK_SHIFT?0x2a:vk;
}
static WORD NtUserVkKeyScanEx(WCHAR c,uintptr_t layout){
    assert(layout==1);if(c>='A'&&c<='Z')return c|0x100;
    if(c>='a'&&c<='z')return c-'a'+'A';if(c>=32&&c<127)return c;return 0xffff;
}
static size_t text_len(const WCHAR *s){size_t n=0;while(s[n])n++;return n;}
static LRESULT send_message(HWND w,UINT msg,WPARAM wp,LPARAM lp){
    assert(w==focus&&current_tid==owner_tid);
    if(msg==WM_GETTEXTLENGTH)return text_len(edit_text);
    if(msg==EM_GETLIMITTEXT)return edit_limit;
    if(msg==WM_GETTEXT){assert(wp>text_len(edit_text));memcpy((void *)lp,edit_text,(text_len(edit_text)+1)*2);return text_len(edit_text);}
    if(msg==EM_SETSEL){assert(!wp&&lp==-1);selections++;return 0;}
    if(msg==EM_REPLACESEL){assert(wp==TRUE);memcpy(edit_text,(void *)lp,(text_len((WCHAR *)lp)+1)*2);replacements++;return 0;}
    assert(0);return 0;
}
static BOOL NtUserSendHardwareInput(HWND w,UINT flags,const INPUT *input,LPARAM lp){
    int alt=0;struct horizon_key_event e={0};
    assert((w==focus||(!w&&(input->ki.dwFlags&KEYEVENTF_KEYUP)))&&!flags&&!lp&&current_tid==owner_tid);
    assert(input->type==INPUT_KEYBOARD);
    assert(event_count<sizeof(events)/sizeof(*events));events[event_count++]=*input;
    horizon_keyboard_event(keyboard_state,&alt,input->ki.wVk,input->ki.wScan,input->ki.dwFlags,0,&e);
    if(input->ki.dwFlags&KEYEVENTF_UNICODE)assert(e.vkey==0xe7&&e.lparam==((uint64_t)input->ki.wScan<<16|1));
    else assert(e.raw.make_code==input->ki.wScan);
    assert(e.message==((input->ki.dwFlags&KEYEVENTF_KEYUP)?0x101:0x100));
    if(!(input->ki.dwFlags&(KEYEVENTF_KEYUP|KEYEVENTF_UNICODE))&&input->ki.wVk>='A'&&input->ki.wVk<='Z'){
        /* Consume actual press/release transitions, including repeated letters. */
        assert(!(keyboard_state[e.vkey]&0x80));
        assert(inserted_count<FX_TEXT_UNITS);
        inserted[inserted_count++]=input->ki.wVk+((keyboard_state[VK_SHIFT]&0x80)?0:'a'-'A');
    }
#ifdef FX_TEST_LIVE_KEYS
    fx_test_live_key(input->ki.wVk,input->ki.dwFlags);
#endif
    horizon_keyboard_update_state(keyboard_state,e.message,e.vkey,0x80);
    /* NtUserCallHwndParam_SendHardwareInput forwards send_hardware_message's
     * NTSTATUS unchanged, despite the BOOL declaration in ntuser.h. */
    return 0;
}
#include "fextendo_keyboard_wine.h"
static void pump(void){milliseconds+=50;fx_wine_text_pump();}
static void drain(void){for(unsigned i=0;i<FX_TEXT_UNITS*3+1&&fx_wine_text.typing;i++)pump();assert(!fx_wine_text.typing);}
static void set_text(const char *s){assert(fx_text_decode(s,strlen(s)+1,edit_text,FX_TEXT_UNITS)>=0);}
static void reset(void){
    memset(&fx_wine_text,0,sizeof(fx_wine_text));
    memset(&fx_keyboard_req,0,sizeof(fx_keyboard_req));memset(&fx_keyboard_result,0,sizeof(fx_keyboard_result));
    fx_keyboard_phase=FX_KBD_IDLE;fx_keyboard_blocked=0;
    fx_keyboard_canceled=fx_keyboard_manual_pending=0;
    memset(fx_keyboard_chords,0,sizeof(fx_keyboard_chords));
    /* The legacy hold scenarios below explicitly select the former delay. */
    fx_keyboard_options=(struct fx_keyboard_options){.hold_ms=600};fx_keyboard_manual_deadline=0;
    fx_keyboard_delivery_done();
    focus_mode=3;focus_changes=focus_fail=restore_fail=show_calls=fx_keyboard_applet_active=0;
    memset(fx_samples,0,sizeof(fx_samples));fx_samples[0].connected=fx_samples[1].connected=1;
    game_paused=show_cancel=show_disconnect=show_hold=0;focus_state=1;
    opens=closes=replacements=selections=0;event_count=0;
    memset(keyboard_state,0,sizeof(keyboard_state));memset(inserted,0,sizeof(inserted));inserted_count=0;
    focus=foreground=10;current_tid=owner_tid=1;style=0;edit_class=visible=enabled=1;caret=0;
    typed="New Save";edit_limit=32;set_text("Old Save");
}
static void codec(void){
    char bytes[FX_TEXT_BYTES];uint16_t out[FX_TEXT_UNITS+1],in[FX_TEXT_UNITS+1]={0};
    /* Every legal scalar, including all surrogate pairs, round trips. */
    for(uint32_t c=32;c<=0x10ffff;c++){
        if(c==127||(c>=0xd800&&c<=0xdfff))continue;
        memset(in,0,sizeof(in));
        if(c<=0xffff)in[0]=c;
        else{in[0]=0xd800+((c-0x10000)>>10);in[1]=0xdc00+((c-0x10000)&1023);}
        int n=fx_text_encode(in,bytes);assert(n>0);
        assert(fx_text_decode(bytes,n+1,out,FX_TEXT_UNITS)>0);
        assert(!memcmp(out,in,(c<=0xffff?2:3)*2));
    }
    const char *bad[]={"\xc0\x80","\xed\xa0\x80","\xf4\x90\x80\x80","\xe2\x82","\x80","\n","\t","\x7f"};
    for(unsigned i=0;i<sizeof(bad)/sizeof(*bad);i++)assert(fx_text_decode(bad[i],strlen(bad[i])+1,out,256)<0);
    assert(fx_text_decode("ab",2,out,256)<0);
    assert(fx_text_decode("abc",4,out,2)<0);
    assert(fx_text_decode("\xf0\x9f\x98\x80",5,out,1)<0);
    memset(in,0,sizeof(in));in[0]=0xd800;assert(fx_text_encode(in,bytes)<0);
    for(unsigned i=0;i<FX_TEXT_UNITS;i++)in[i]='a';in[FX_TEXT_UNITS]=0;
    assert(fx_text_encode(in,bytes)==256&&fx_text_decode(bytes,257,out,256)==256);
}
int main(void){
    codec();reset();
    pump();assert(fx_keyboard_phase==FX_KBD_PENDING&&fx_keyboard_input_blocked());
    assert(!fx_keyboard_request(&fx_wine_text.request)); /* one applet request at a time */
    fx_keyboard_service();assert(opens==1&&closes==1&&last_limit==32&&!strcmp(last_initial,"Old Save"));
    assert(focus_changes==2&&focus_mode==3&&!fx_keyboard_applet_active);
    pump();assert(replacements==1&&selections==1&&edit_text[0]=='N'&&!event_count);
    pump();fx_keyboard_service();assert(opens==1); /* no reopen loop */
    reset();show_cancel=1;pump();fx_keyboard_service();pump();assert(!replacements&&edit_text[0]=='O');
    assert(focus_changes==2&&focus_mode==3&&!fx_keyboard_applet_active);
    reset();focus_fail=1;pump();fx_keyboard_service();pump();
    assert(!show_calls&&!replacements&&closes==1&&focus_changes==2&&focus_mode==3&&!fx_keyboard_applet_active);
    reset();restore_fail=1;pump();fx_keyboard_service();pump();
    assert(show_calls==1&&!replacements&&closes==1&&focus_changes==2&&!fx_keyboard_applet_active);
    reset();typed="";pump();fx_keyboard_service();pump();assert(replacements==1&&!edit_text[0]);
    reset();edit_limit=3;set_text("Old");typed="Too long";pump();fx_keyboard_service();pump();assert(!replacements);
    reset();pump();fx_keyboard_service();set_text("Changed elsewhere");pump();assert(!replacements&&!selections);
    reset();pump();focus=foreground=11;pump();assert(!fx_keyboard_take(1,&fx_keyboard_result));
    assert(fx_keyboard_phase==FX_KBD_IDLE);pump();
    assert(fx_keyboard_phase==FX_KBD_PENDING); /* new field, old request discarded */
    fx_keyboard_service();pump();assert(replacements==1);
    reset();pump();fx_keyboard_service();focus=foreground=0;pump();assert(!replacements&&fx_keyboard_phase==FX_KBD_IDLE);
    reset();pump();wine_nx_drv_DestroyWindow(focus);assert(fx_keyboard_phase==FX_KBD_IDLE);
    reset();pump();show_hold=1;fx_keyboard_service();pump();assert(!replacements&&fx_keyboard_input_blocked());
    fx_samples[1].buttons=0;fx_keyboard_service();pump();assert(replacements==1&&!fx_keyboard_input_blocked());
    reset();pump();show_disconnect=1;fx_keyboard_service();assert(game_paused);
    /* Reconnect may remain paused over many monitor iterations. */
    fx_keyboard_cancel_all();fx_keyboard_cancel_all();pump();assert(!fx_wine_text.token);
    assert(!replacements);
    reset();pump();fx_keyboard_service();game_paused=1;fx_keyboard_cancel_all();pump();assert(!replacements);
    reset();edit_class=0;pump();assert(!fx_wine_text.token); /* main game focus is insufficient */
    wine_nx_drv_NotifyIMEStatus(focus,1);pump();assert(!fx_wine_text.token);
    wine_nx_drv_SetIMECompositionRect(focus,(RECT){0});pump();assert(fx_wine_text.token);
    typed="A\xc3\xa9\xf0\x9f\x98\x80";fx_keyboard_service();pump();drain();
    assert(event_count==10&&events[0].ki.wVk==VK_SHIFT&&events[1].ki.wVk=='A');
    assert(events[4].ki.wScan==0xe9&&events[6].ki.wScan==0xd83d&&events[8].ki.wScan==0xde00);
    pump();assert(event_count==10); /* exactly once, no Enter or duplicate text */
    wine_nx_drv_NotifyIMEStatus(focus,0);pump();
    wine_nx_drv_NotifyIMEStatus(focus,1);wine_nx_drv_SetIMECompositionRect(focus,(RECT){0});pump();assert(fx_wine_text.token);
    reset();edit_class=0;caret=focus;pump();assert(fx_wine_text.token);
    reset();caret=focus;style=ES_READONLY;pump();assert(!fx_wine_text.token);
    reset();caret=focus;style=ES_PASSWORD;pump();assert(!fx_wine_text.token);
    reset();owner_tid=2;pump();assert(!fx_wine_text.token);
    reset();foreground=11;pump();assert(!fx_wine_text.token);
    /* A manual request must not truncate on a transient caret/IME change
     * after the first key. The old implementation produces only "H" here. */
    for(unsigned signal=2;signal<=3;signal++){
        reset();edit_class=0;fx_keyboard_manual_pending=1;
        if(signal==3)caret=focus;
        else{wine_nx_drv_NotifyIMEStatus(focus,1);wine_nx_drv_SetIMECompositionRect(focus,(RECT){0});}
        pump();typed="Hallo";fx_keyboard_service();pump();pump();
        assert(!strcmp(inserted,"H")&&fx_wine_text.down);
        if(signal==3)caret=0;else wine_nx_drv_NotifyIMEStatus(focus,0);
        drain();assert(!strcmp(inserted,"Hallo"));
        assert(!fx_keyboard_input_blocked()&&!(keyboard_state[VK_SHIFT]&0x80));
    }
    reset();edit_class=0;
    fx_samples[0]=fx_pad_normalize(FX_PAD_RIGHT,1,FX_PAD_SL|FX_PAD_SR|FX_PAD_RSTICK,0,0,0,0);
    fx_keyboard_poll_locked();ticks+=600;fx_keyboard_poll_locked();
    assert(!fx_keyboard_input_blocked()&&fx_keyboard_manual_pending);
    pump();assert(fx_wine_text.kind==4&&fx_wine_text.token);
    fx_keyboard_poll_locked();assert(!fx_keyboard_manual_pending); /* one per click */
    fx_samples[0].buttons=0;fx_keyboard_poll_locked();fx_keyboard_service();pump();drain();
    assert(event_count==strlen(typed)*2+4); /* Shift down/up for N and S */
    assert(!fx_keyboard_input_blocked());
    /* Short presses never swallow input when a hold is selected;
     * single Joy-Con always has its SL/SR + stick equivalent. */
    const unsigned styles[]={FX_PAD_FULL,FX_PAD_LEFT,FX_PAD_RIGHT};
    for(unsigned choice=0;choice<4;choice++)for(unsigned i=0;i<3;i++)for(unsigned player=0;player<1;player++){
        reset();
        fx_keyboard_options.shortcut=choice;
        uint64_t shoulders=i?FX_PAD_SL|FX_PAD_SR:FX_PAD_L|FX_PAD_R;
        uint64_t stick=i==2?FX_PAD_RSTICK:FX_PAD_LSTICK;
        fx_samples[player]=fx_pad_normalize(styles[i],1,shoulders,0,0,0,0);
        fx_keyboard_poll_locked();assert(!fx_keyboard_manual());
        fx_samples[player]=fx_pad_normalize(styles[i],1,shoulders|stick,0,0,0,0);
        if(!i)fx_samples[player].buttons=fx_keyboard_chord_mask(choice,styles[i]);
        fx_keyboard_poll_locked();assert(!fx_keyboard_manual()&&!fx_keyboard_input_blocked());
        ticks+=599;fx_keyboard_poll_locked();assert(!fx_keyboard_manual());
        ticks++;fx_keyboard_poll_locked();assert(fx_keyboard_manual()&&fx_keyboard_manual_owner()==player);
        fx_keyboard_poll_locked();assert(!fx_keyboard_manual());
        fx_samples[player]=fx_pad_normalize(styles[i],1,0,0,0,0,0);
        fx_keyboard_poll_locked();assert(!fx_keyboard_manual());
        fx_samples[player]=fx_pad_normalize(styles[i],1,shoulders|stick,0,0,0,0);
        if(!i)fx_samples[player].buttons=fx_keyboard_chord_mask(choice,styles[i]);
        fx_keyboard_poll_locked();ticks+=600;fx_keyboard_poll_locked();assert(fx_keyboard_manual());
    }
    reset();fx_samples[1].buttons=FX_PAD_L|FX_PAD_R|FX_PAD_LSTICK;
    fx_keyboard_poll_locked();ticks+=600;fx_keyboard_poll_locked();assert(!fx_keyboard_manual());
    reset();fx_samples[0].buttons=FX_PAD_LSTICK;fx_keyboard_poll_locked();
    fx_samples[0].buttons|=FX_PAD_L|FX_PAD_R;fx_keyboard_poll_locked();
    assert(!fx_keyboard_manual()&&!fx_keyboard_input_blocked());
    fx_samples[0].buttons=FX_PAD_A;fx_samples[0].lx=24000;fx_samples[1].buttons=FX_PAD_B;
    for(int n=0;n<100;n++){ticks+=20;fx_keyboard_poll_locked();assert(!fx_keyboard_input_blocked());}
    /* Previously the chord latched input off until BOTH pads/sticks were
     * neutral, even though no manual request had been accepted. */
    reset();fx_samples[0].buttons=FX_PAD_L|FX_PAD_LSTICK;fx_samples[1].buttons=FX_PAD_R;
    fx_keyboard_poll_locked();assert(!fx_keyboard_manual()); /* Never combine different players. */
    ticks+=600;fx_keyboard_poll_locked();assert(!fx_keyboard_manual()&&!fx_keyboard_input_blocked());
    reset();fx_samples[0].buttons=FX_PAD_L|FX_PAD_R|FX_PAD_LSTICK;
    fx_keyboard_poll_locked();ticks+=600;fx_keyboard_poll_locked();ticks+=1001;
    assert(!fx_keyboard_manual()&&!fx_keyboard_input_blocked()); /* Stalled Wine cannot reopen a stale request. */
    for(int reason=0;reason<4;reason++){
        reset();fx_samples[0].buttons=FX_PAD_L|FX_PAD_R|FX_PAD_LSTICK;
        if(reason==0)focus_state=0;
        if(reason==1)game_paused=1;
        if(reason==2)fx_game_active=0;
        if(reason==3)fx_keyboard_options.shortcut=4;
        fx_keyboard_poll_locked();ticks+=600;fx_keyboard_poll_locked();assert(!fx_keyboard_manual());
        focus_state=fx_game_active=1;game_paused=0;fx_keyboard_options.shortcut=0;
        fx_keyboard_poll_locked();assert(!fx_keyboard_manual());
    }
    reset();edit_class=0;fx_keyboard_manual_pending=1;pump();typed="ABC";fx_keyboard_service();pump();pump();
    assert(fx_wine_text.down&&fx_wine_text.shift&&fx_keyboard_input_blocked());
    focus=foreground=11;pump();assert(!fx_wine_text.down&&!fx_wine_text.shift&&!fx_keyboard_input_blocked());
    assert(event_count==4); /* Abort releases the only pressed character + Shift. */
    reset();edit_class=0;fx_keyboard_manual_pending=1;pump();typed="ABC";fx_keyboard_service();pump();pump();
    game_paused=1;fx_keyboard_cancel_all();pump();
    assert(event_count==4&&!fx_wine_text.down&&!fx_wine_text.shift&&!fx_keyboard_delivering());
    puts("PASS: Unicode scalars, native queue/cancel/drain/reconnect, Wine focus/IME/Edit/custom delivery, horizontal shortcut");
    return 0;
}
