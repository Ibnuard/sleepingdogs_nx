/* LGPL-2.1-or-later. Short queue locks only; no Wine calls, VI or pad lock
 * while holding this mutex. The monitor handles display and neutral drain. */
enum fx_osk_phase { FX_OSK_IDLE,FX_OSK_PENDING,FX_OSK_OPEN,FX_OSK_ABORT,FX_OSK_DRAIN };
static struct fx_osk_core fx_osk_state;
static enum fx_osk_phase fx_osk_phase;
static uint64_t fx_osk_serial;
static unsigned fx_osk_player;
static int fx_osk_blocking,fx_osk_unclaimed;
#ifndef FX_OSK_TRACE
#define FX_OSK_TRACE(...) ((void)0)
#endif
int fx_osk_blocked(void){return __atomic_load_n(&fx_osk_blocking,__ATOMIC_ACQUIRE);}
uint64_t fx_osk_open(unsigned player) {
    uint64_t token=0;
    if(player!=0||!__atomic_load_n(&fx_keyboard_ready,__ATOMIC_ACQUIRE)||fx_pads_paused()||
       fx_keyboard_delivering()||__atomic_load_n(&fx_keyboard_blocked,__ATOMIC_ACQUIRE))return 0;
    pthread_mutex_lock(&fx_keyboard_lock);
    if(fx_osk_phase==FX_OSK_IDLE&&fx_keyboard_phase==FX_KBD_IDLE&&!fx_keyboard_delivering()){
        memset(&fx_osk_state,0,sizeof(fx_osk_state));fx_osk_state.generation=1;fx_osk_state.selected=24;
        fx_osk_state.top=fx_keyboard_options.top;
        fx_osk_player=player;if(!++fx_osk_serial)++fx_osk_serial;token=fx_osk_serial;
        fx_osk_unclaimed=1;
        fx_osk_phase=FX_OSK_PENDING;__atomic_store_n(&fx_osk_blocking,1,__ATOMIC_RELEASE);
    }
    pthread_mutex_unlock(&fx_keyboard_lock);
    if(token)FX_OSK_TRACE("[OSK] request token=%llu player=%u top=%d",(unsigned long long)token,player+1,fx_keyboard_options.top);
    return token;
}
/* Display activation belongs to the native monitor. Wine claims a pending
 * session on the focused window's thread before sending any keyboard input.
 * A game that rarely pumps window events must not lose its shortcut request. */
uint64_t fx_osk_claim(void) {
    uint64_t token=0;pthread_mutex_lock(&fx_keyboard_lock);
    if(fx_osk_unclaimed&&(fx_osk_phase==FX_OSK_PENDING||fx_osk_phase==FX_OSK_OPEN)){
        token=fx_osk_serial;fx_osk_unclaimed=0;
    }
    pthread_mutex_unlock(&fx_keyboard_lock);return token;
}
int fx_osk_valid(uint64_t token) {
    int valid;pthread_mutex_lock(&fx_keyboard_lock);
    valid=token&&token==fx_osk_serial&&(fx_osk_phase==FX_OSK_PENDING||fx_osk_phase==FX_OSK_OPEN)&&!fx_pads_paused();
    pthread_mutex_unlock(&fx_keyboard_lock);return valid;
}
int fx_osk_next(uint64_t token,struct fx_osk_key *key) {
    int status=-1;pthread_mutex_lock(&fx_keyboard_lock);
    if(token&&token==fx_osk_serial&&!fx_pads_paused()){
        if(fx_osk_phase==FX_OSK_PENDING)status=0;
        else if(fx_osk_phase==FX_OSK_OPEN){status=fx_osk_dequeue(&fx_osk_state,key);if(!status&&fx_osk_state.closing)status=-1;}
    }
    pthread_mutex_unlock(&fx_keyboard_lock);return status;
}
void fx_osk_abort(uint64_t token) {
    if(!fx_osk_blocked())return;
    pthread_mutex_lock(&fx_keyboard_lock);
    if((!token||token==fx_osk_serial)&&(fx_osk_phase==FX_OSK_PENDING||fx_osk_phase==FX_OSK_OPEN)){
        fx_osk_phase=FX_OSK_ABORT;fx_osk_state.count=0;
    }
    pthread_mutex_unlock(&fx_keyboard_lock);
}
void fx_osk_finished(uint64_t token) {
    pthread_mutex_lock(&fx_keyboard_lock);
    if(token&&token==fx_osk_serial&&fx_osk_phase!=FX_OSK_IDLE){fx_osk_phase=FX_OSK_DRAIN;fx_osk_state.count=0;}
    pthread_mutex_unlock(&fx_keyboard_lock);
}
/* No key can be sent while PENDING. A failed first surface therefore needs
 * no Wine acknowledgement, even if the window thread already claimed it.
 * After OPEN, retain the normal acknowledgement to release injected keys. */
static void fx_osk_display_failed(uint64_t token) {
    pthread_mutex_lock(&fx_keyboard_lock);
    if(token==fx_osk_serial){
        if(fx_osk_phase==FX_OSK_PENDING){
            fx_osk_phase=FX_OSK_DRAIN;fx_osk_state.count=0;fx_osk_unclaimed=0;
        }else if(fx_osk_phase==FX_OSK_OPEN){fx_osk_phase=FX_OSK_ABORT;fx_osk_state.count=0;}
    }
    pthread_mutex_unlock(&fx_keyboard_lock);
}
static void fx_osk_service(void) {
    if(!fx_osk_blocked()&&fx_keyboard_manual())fx_osk_open(0);
    if(!fx_osk_blocked())return;
    if(fx_pads_paused()||appletGetFocusState()!=AppletFocusState_InFocus)fx_osk_abort(0);
    struct fx_pad_sample pads[2];fx_pads_snapshot(pads);
    int x=0,y=0,touching=fx_osk_touch(&x,&y);
    int neutral=fx_pad_neutral(&pads[0]);
    struct fx_osk_core view;unsigned player;enum fx_osk_phase phase;uint64_t token;
    pthread_mutex_lock(&fx_keyboard_lock);phase=fx_osk_phase;player=fx_osk_player;token=fx_osk_serial;
    if(phase==FX_OSK_OPEN){
        if(!fx_osk_state.top)y-=720-FX_OSK_HEIGHT;
        uint64_t ms=armGetSystemTick()/(armGetSystemTickFreq()/1000);
        fx_osk_input(&fx_osk_state,&pads[player],neutral,touching,x,y,ms);
    }
    /* Closing/focus loss also works before Wine has claimed the session. */
    if(fx_osk_unclaimed&&(phase==FX_OSK_ABORT||fx_osk_state.closing)){
        phase=fx_osk_phase=FX_OSK_DRAIN;fx_osk_state.count=0;fx_osk_unclaimed=0;
    }
    view=fx_osk_state;pthread_mutex_unlock(&fx_keyboard_lock);
    if(phase==FX_OSK_PENDING||phase==FX_OSK_OPEN){
        int single=pads[player].kind==FX_PAD_LEFT?1:pads[player].kind==FX_PAD_RIGHT?2:0;
        int shown=fx_osk_display_show(&view,player,single);
        if(!shown)fx_osk_display_failed(token);
        else if(shown==1&&phase==FX_OSK_PENDING){
            pthread_mutex_lock(&fx_keyboard_lock);if(fx_osk_phase==FX_OSK_PENDING)fx_osk_phase=FX_OSK_OPEN;pthread_mutex_unlock(&fx_keyboard_lock);
        }
    }else{
        fx_osk_display_close();
        if(phase==FX_OSK_DRAIN&&neutral&&!touching&&appletGetFocusState()==AppletFocusState_InFocus){
            pthread_mutex_lock(&fx_keyboard_lock);fx_osk_phase=FX_OSK_IDLE;
            __atomic_store_n(&fx_osk_blocking,0,__ATOMIC_RELEASE);pthread_mutex_unlock(&fx_keyboard_lock);
            FX_OSK_TRACE("[OSK] input restored token=%llu",(unsigned long long)token);
        }
    }
}
