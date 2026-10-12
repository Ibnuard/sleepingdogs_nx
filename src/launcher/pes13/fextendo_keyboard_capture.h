/* LGPL-2.1-or-later. Capture is an applet notification, not an Npad bit.
 * It carries no controller ID: either controller may request the P1 OSK.
 * Only the game monitor registers/removes the hook. A callback just sets a
 * latch; display/input work stays in the existing monitor, outside libnx. */
static AppletHookCookie fx_keyboard_capture_cookie;
static int fx_keyboard_capture_registered,fx_keyboard_capture_enabled,fx_keyboard_capture_pending;
static void fx_keyboard_capture_hook(AppletHookType hook,void *unused) {
    (void)unused;
    if(hook==AppletHookType_OnCaptureButtonShortPressed&&
       __atomic_load_n(&fx_keyboard_capture_enabled,__ATOMIC_ACQUIRE))
        __atomic_store_n(&fx_keyboard_capture_pending,1,__ATOMIC_RELEASE);
}
static void fx_keyboard_capture_stop(void) {
    int enabled=__atomic_exchange_n(&fx_keyboard_capture_enabled,0,__ATOMIC_ACQ_REL);
    __atomic_store_n(&fx_keyboard_capture_pending,0,__ATOMIC_RELEASE);
    if(enabled){
        Result rc=appletSetRequiresCaptureButtonShortPressedMessage(false);
        if(R_FAILED(rc))FX_OSK_TRACE("[OSK] Capture restore failed rc=0x%x",(unsigned)rc);
    }
    if(fx_keyboard_capture_registered){appletUnhook(&fx_keyboard_capture_cookie);fx_keyboard_capture_registered=0;}
}
static void fx_keyboard_capture_start(void) {
    if(fx_keyboard_options.shortcut!=FX_KEYBOARD_CAPTURE||fx_keyboard_capture_registered)return;
    appletHook(&fx_keyboard_capture_cookie,fx_keyboard_capture_hook,NULL);fx_keyboard_capture_registered=1;
    Result rc=appletSetRequiresCaptureButtonShortPressedMessage(true);
    if(R_FAILED(rc)){
        FX_OSK_TRACE("[OSK] Capture shortcut unavailable rc=0x%x",(unsigned)rc);
        fx_keyboard_capture_stop();return;
    }
    __atomic_store_n(&fx_keyboard_capture_enabled,1,__ATOMIC_RELEASE);
    FX_OSK_TRACE("[OSK] Capture shortcut enabled; either controller opens P1 keyboard");
}
static void fx_keyboard_capture_poll(void) {
    if(!__atomic_exchange_n(&fx_keyboard_capture_pending,0,__ATOMIC_ACQ_REL))return;
    if(!__atomic_load_n(&fx_keyboard_capture_enabled,__ATOMIC_ACQUIRE)||
       !fx_game_active||!__atomic_load_n(&fx_keyboard_ready,__ATOMIC_ACQUIRE)||
       appletGetFocusState()!=AppletFocusState_InFocus||fx_pads_paused()||fx_keyboard_input_blocked())return;
    /* Serialize with chord producers. No VI, Wine or applet call under this
     * lock. No held-button delay applies to the system's short-press event. */
    pthread_mutex_lock(&fx_pad_lock);
    if(!__atomic_load_n(&fx_keyboard_manual_pending,__ATOMIC_ACQUIRE)){
        __atomic_store_n(&fx_keyboard_manual_player,0,__ATOMIC_RELEASE);
        __atomic_store_n(&fx_keyboard_manual_deadline,fx_keyboard_now_ms()+1000,__ATOMIC_RELEASE);
        __atomic_store_n(&fx_keyboard_manual_pending,1,__ATOMIC_RELEASE);
    }
    pthread_mutex_unlock(&fx_pad_lock);
    FX_OSK_TRACE("[OSK] Capture request queued for Player 1");
}
