/* LGPL-2.1-or-later. Included by winnx_drv.c, never by a plain native worker.
 * Every Win32 call below runs on the window's own Wine thread. */
#include "fextendo_keyboard.h"
static _Thread_local struct {
    HWND seen_focus,seen_candidate,ime_window,target;
    unsigned ime_open,ime_rect,seen_kind,kind;
    uint64_t token;
    int pumping,manual_custom;
    DWORD last_poll;
    struct fx_text_request request;
    uint16_t pending[FX_TEXT_UNITS+1];
    unsigned position;
    int typing,shift,down;
    INPUT held;
#ifdef FX_KEYBOARD_OVERLAY
    uint64_t overlay;
    struct fx_osk_key overlay_key;
    unsigned overlay_stage;
#endif
} fx_wine_text;

static BOOL fx_wine_text_send(HWND hwnd,const INPUT *input) {
    /* ntuser.h declares BOOL, but NtUserCallHwndParam_SendHardwareInput
     * returns send_hardware_message's NTSTATUS: zero means SUCCESS.
     * Interpreting it as BOOL truncates the text after the first event. */
    return NtUserSendHardwareInput(hwnd,0,input,0)==0;
}
static INPUT fx_wine_text_key(UINT vk,DWORD flags) {
    INPUT input={0};UINT scan=NtUserMapVirtualKeyEx(vk,MAPVK_VK_TO_VSC_EX,NtUserGetKeyboardLayout(0));
    input.type=INPUT_KEYBOARD;input.ki.wVk=vk;input.ki.wScan=scan&0xff;input.ki.dwFlags=flags;
    if((scan&0xff00)==0xe000)input.ki.dwFlags|=KEYEVENTF_EXTENDEDKEY;
    return input;
}
static void fx_wine_text_release(void) {
    if(fx_wine_text.down){
        fx_wine_text.held.ki.dwFlags|=KEYEVENTF_KEYUP;
        fx_wine_text_send(0,&fx_wine_text.held);fx_wine_text.down=0;
    }
    if(fx_wine_text.shift){
        INPUT key=fx_wine_text_key(VK_SHIFT,KEYEVENTF_KEYUP);
        fx_wine_text_send(0,&key);fx_wine_text.shift=0;
    }
}
static void fx_wine_text_stop(void) {
    fx_wine_text_release();memset(fx_wine_text.pending,0,sizeof(fx_wine_text.pending));
    fx_wine_text.typing=0;fx_keyboard_delivery_done();
}

static int fx_wine_text_focus(HWND hwnd) {
    HWND foreground=NtUserGetForegroundWindow();
    return hwnd&&hwnd==get_focus()&&get_window_thread(hwnd,NULL)==GetCurrentThreadId()&&
        is_window_visible(hwnd)&&is_window_enabled(hwnd)&&foreground&&
        NtUserGetAncestor(hwnd,GA_ROOT)==NtUserGetAncestor(foreground,GA_ROOT);
}
static int fx_wine_text_edit(HWND hwnd) {
    WCHAR chars[32]={0};UNICODE_STRING name={0,sizeof(chars),chars};
    if(NtUserGetClassName(hwnd,FALSE,&name)!=4)return 0;
    return (chars[0]=='E'||chars[0]=='e')&&(chars[1]=='D'||chars[1]=='d')&&
        (chars[2]=='I'||chars[2]=='i')&&(chars[3]=='T'||chars[3]=='t');
}
static unsigned fx_wine_text_kind(HWND hwnd) {
    GUITHREADINFO info={.cbSize=sizeof(info)};
    if(!fx_wine_text_focus(hwnd))return 0;
    if(fx_wine_text_edit(hwnd))return
        (NtUserGetWindowLongW(hwnd,GWL_STYLE)&(ES_READONLY|ES_PASSWORD|ES_MULTILINE))?0:1;
    if(fx_wine_text.ime_window==hwnd&&fx_wine_text.ime_open&&fx_wine_text.ime_rect)return 2;
    /* A system caret is an explicit text-entry signal. A game drawing its own
     * cursor does not qualify; use the manual shortcut for those screens. */
    if(NtUserGetGUIThreadInfo(GetCurrentThreadId(),&info)&&info.hwndCaret==hwnd)return 3;
    return 0;
}
static int fx_wine_text_target_valid(unsigned kind) {
    /* IME/caret state is an opening hint, not the lifetime of a manually
     * selected game field. PES may dismiss that hint after its first key.
     * Keep explicit custom entry bound to its focused window until done;
     * automatic detection and standard Edit retain their kind checks. */
    return fx_wine_text_focus(fx_wine_text.target)&&
        (fx_wine_text.manual_custom||fx_wine_text.kind==4||kind==fx_wine_text.kind);
}
#ifdef FX_KEYBOARD_OVERLAY
static void fx_wine_osk_stop(void) {
    fx_osk_abort(fx_wine_text.overlay);fx_wine_text_release();
    fx_osk_finished(fx_wine_text.overlay);fx_wine_text.overlay=0;fx_wine_text.overlay_stage=0;
}
static BOOL fx_wine_osk_pump(void) {
    if(!fx_osk_valid(fx_wine_text.overlay)||!fx_wine_text_focus(fx_wine_text.target)){
        fx_wine_osk_stop();return FALSE;
    }
    if(!fx_wine_text.overlay_stage){
        int next=fx_osk_next(fx_wine_text.overlay,&fx_wine_text.overlay_key);
        if(next<0){fx_wine_osk_stop();return FALSE;}
        if(!next)return FALSE;
        if(fx_wine_text.overlay_key.character){
            WORD packed=NtUserVkKeyScanEx(fx_wine_text.overlay_key.character,NtUserGetKeyboardLayout(0));
            if(packed==0xffff||(packed>>8)>1){fx_wine_osk_stop();return FALSE;}
            fx_wine_text.overlay_key.vk=packed&255;
            if(packed>>8){
                INPUT key=fx_wine_text_key(VK_SHIFT,0);
                if(!fx_wine_text_send(fx_wine_text.target,&key)){fx_wine_osk_stop();return FALSE;}
                fx_wine_text.shift=1;fx_wine_text.overlay_stage=1;return TRUE;
            }
        }
        fx_wine_text.overlay_stage=1;
    }
    if(fx_wine_text.overlay_stage==1){
        fx_wine_text.held=fx_wine_text_key(fx_wine_text.overlay_key.vk,0);
        if(!fx_wine_text_send(fx_wine_text.target,&fx_wine_text.held)){fx_wine_osk_stop();return FALSE;}
        fx_wine_text.down=1;fx_wine_text.overlay_stage=2;
    }else if(fx_wine_text.overlay_stage==2){
        fx_wine_text.held.ki.dwFlags|=KEYEVENTF_KEYUP;
        if(!fx_wine_text_send(0,&fx_wine_text.held)){fx_wine_osk_stop();return FALSE;}
        fx_wine_text.down=0;fx_wine_text.overlay_stage=fx_wine_text.shift?3:0;
    }else{
        INPUT key=fx_wine_text_key(VK_SHIFT,KEYEVENTF_KEYUP);
        if(!fx_wine_text_send(0,&key)){fx_wine_osk_stop();return FALSE;}
        fx_wine_text.shift=0;fx_wine_text.overlay_stage=0;
    }
    return TRUE;
}
#endif
void wine_nx_drv_NotifyIMEStatus(HWND hwnd,UINT status) {
    if(!status||fx_wine_text.ime_window!=hwnd)fx_wine_text.ime_rect=0;
    fx_wine_text.ime_window=hwnd;fx_wine_text.ime_open=!!status;
    if(!status&&fx_wine_text.seen_kind==2){fx_wine_text.seen_candidate=0;fx_wine_text.seen_kind=0;}
}
BOOL wine_nx_drv_SetIMECompositionRect(HWND hwnd,RECT rect) {
    (void)rect;
    if(fx_wine_text.ime_window!=hwnd){fx_wine_text.ime_window=hwnd;fx_wine_text.ime_open=0;}
    fx_wine_text.ime_rect=1;return TRUE;
}
void wine_nx_drv_DestroyWindow(HWND hwnd) {
#ifdef FX_KEYBOARD_OVERLAY
    if(fx_wine_text.target==hwnd&&fx_wine_text.overlay)fx_wine_osk_stop();
#endif
    if(fx_wine_text.target==hwnd&&fx_wine_text.token){
        fx_keyboard_cancel(fx_wine_text.token);fx_wine_text.token=0;
    }
    if(fx_wine_text.target==hwnd&&fx_wine_text.typing)fx_wine_text_stop();
    if(fx_wine_text.ime_window==hwnd){fx_wine_text.ime_window=0;fx_wine_text.ime_open=fx_wine_text.ime_rect=0;}
    if(fx_wine_text.seen_focus==hwnd)fx_wine_text.seen_focus=fx_wine_text.seen_candidate=0;
}
static BOOL fx_wine_text_pump(void) {
    struct fx_text_result result;HWND focus;unsigned kind;BOOL sent=FALSE;
    DWORD now=NtGetTickCount();
    if(fx_wine_text.pumping||now-fx_wine_text.last_poll<50)return FALSE;
    fx_wine_text.last_poll=now;
    fx_wine_text.pumping=1;focus=get_focus();
    if(focus!=fx_wine_text.seen_focus){
        fx_wine_text.seen_focus=focus;fx_wine_text.seen_candidate=0;fx_wine_text.seen_kind=0;
    }
    kind=fx_wine_text_kind(focus);
#ifdef FX_KEYBOARD_OVERLAY
    if(fx_wine_text.overlay){sent=fx_wine_osk_pump();goto done;}
#endif
    if(fx_wine_text.typing){
        if(!fx_keyboard_delivering()||!fx_wine_text_target_valid(kind)){fx_wine_text_stop();goto done;}
        if(fx_wine_text.down){fx_wine_text_release();fx_wine_text.position++;sent=TRUE;goto done;}
        uint16_t c=fx_wine_text.pending[fx_wine_text.position];
        if(!c){fx_wine_text_stop();goto done;}
        WORD packed=NtUserVkKeyScanEx(c,NtUserGetKeyboardLayout(0));
        if(c<128&&packed!=0xffff&&(packed>>8)<=1){
            /* Real scan codes follow the tested keyboard fallback and are
             * visible to DirectInput. Hold each key for a pump interval so
             * games polling GetDeviceState also observe it. */
            if(packed>>8){
                INPUT shift=fx_wine_text_key(VK_SHIFT,0);
                if(!fx_wine_text_send(focus,&shift)){fx_wine_text_stop();goto done;}
                fx_wine_text.shift=1;
            }
            fx_wine_text.held=fx_wine_text_key(packed&255,0);
            if(!fx_wine_text_send(focus,&fx_wine_text.held)){fx_wine_text_stop();goto done;}
            fx_wine_text.down=1;sent=TRUE;
        }else{
            /* Non-ASCII input uses VK_PACKET. Keep a surrogate pair together. */
            unsigned count=(c>=0xd800&&c<=0xdbff)?2:1;
            while(count--){
                INPUT input={0};input.type=INPUT_KEYBOARD;
                input.ki.wScan=fx_wine_text.pending[fx_wine_text.position++];input.ki.dwFlags=KEYEVENTF_UNICODE;
                if(!fx_wine_text_send(focus,&input)){fx_wine_text_stop();goto done;}
                input.ki.dwFlags|=KEYEVENTF_KEYUP;fx_wine_text_send(focus,&input);sent=TRUE;
            }
        }
        goto done;
    }
    if(fx_wine_text.token){
        if(!fx_wine_text_target_valid(kind)){
            fx_keyboard_cancel(fx_wine_text.token);fx_wine_text.token=0;
        }else if(fx_keyboard_take(fx_wine_text.token,&result)){
            fx_wine_text.token=0;
            if(result.accepted){
                if(fx_wine_text.kind==1){
                    fx_keyboard_delivery_done();
                    WCHAR current[FX_TEXT_UNITS+1]={0};
                    LRESULT len=send_message(focus,WM_GETTEXTLENGTH,0,0);
                    if(len<0||len>FX_TEXT_UNITS)goto done;
                    send_message(focus,WM_GETTEXT,FX_TEXT_UNITS+1,(LPARAM)current);
                    /* Do not overwrite text edited while the applet was open. */
                    if(memcmp(current,fx_wine_text.request.initial,(len+1)*sizeof(WCHAR)))goto done;
                    if(!fx_wine_text_focus(focus))goto done;
                    send_message(focus,EM_SETSEL,0,-1);
                    if(fx_wine_text_focus(focus))send_message(focus,EM_REPLACESEL,TRUE,(LPARAM)result.text);
                    sent=TRUE;
                }else{
                    memcpy(fx_wine_text.pending,result.text,sizeof(result.text));
                    fx_wine_text.position=0;fx_wine_text.typing=1;
                }
            }
        }
        goto done;
    }
    if(!kind){fx_wine_text.seen_candidate=0;fx_wine_text.seen_kind=0;}
    if(!fx_wine_text_focus(focus))goto done;
#ifdef FX_KEYBOARD_OVERLAY
    /* Adopt the monitor's shortcut session without waiting for a second chord.
     * Window APIs and input delivery remain on this Wine window thread. */
    fx_wine_text.overlay=fx_osk_claim();
    if(fx_wine_text.overlay){
        fx_wine_text.target=focus;fx_wine_text.kind=kind?kind:4;goto done;
    }
#endif
    int manual=fx_keyboard_manual();
    if(!manual&&(!kind||(fx_wine_text.seen_candidate==focus&&fx_wine_text.seen_kind==kind)))goto done;
    if(!kind)kind=4; /* Explicit shortcut on the current game's custom UI. */
#ifdef FX_KEYBOARD_OVERLAY
    if(kind!=1){
        fx_wine_text.overlay=fx_osk_open(manual?fx_keyboard_manual_owner():0);
        if(fx_wine_text.overlay){
            fx_osk_claim();
            fx_wine_text.target=focus;fx_wine_text.kind=kind;
            fx_wine_text.seen_candidate=focus;fx_wine_text.seen_kind=kind;
        }
        goto done;
    }
#endif
    memset(&fx_wine_text.request,0,sizeof(fx_wine_text.request));
    fx_wine_text.request.window=(uintptr_t)focus;
    fx_wine_text.request.thread=GetCurrentThreadId();fx_wine_text.request.limit=FX_TEXT_UNITS;
    if(kind==1){
        LRESULT len=send_message(focus,WM_GETTEXTLENGTH,0,0);
        LRESULT limit=send_message(focus,EM_GETLIMITTEXT,0,0);
        if(len<0||len>FX_TEXT_UNITS)goto done;
        if(limit>0&&limit<FX_TEXT_UNITS)fx_wine_text.request.limit=limit;
        if(len>fx_wine_text.request.limit)goto done;
        send_message(focus,WM_GETTEXT,FX_TEXT_UNITS+1,(LPARAM)fx_wine_text.request.initial);
    }
    if(!fx_wine_text_focus(focus))goto done;
    fx_wine_text.token=fx_keyboard_request(&fx_wine_text.request);
    if(fx_wine_text.token){
        fx_wine_text.target=focus;fx_wine_text.kind=kind;
        fx_wine_text.manual_custom=manual&&kind!=1;
        fx_wine_text.seen_candidate=focus;fx_wine_text.seen_kind=kind;
    }
done:
    fx_wine_text.pumping=0;return sent;
}
