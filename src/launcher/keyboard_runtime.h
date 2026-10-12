/* SPDX-License-Identifier: LGPL-2.1-or-later.
 * Single-player adapter for the pinned PES13 keyboard. Sleeping Dogs keeps
 * its existing XInput mapping. Only keyboard sessions suppress game input.
 */
#define FX_KEYBOARD_OVERLAY 1
#include "pes13/fextendo_keyboard.h"
static pthread_mutex_t fx_pad_lock=PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t fx_pad_applet_lock=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t fx_pad_cond=PTHREAD_COND_INITIALIZER;
static struct fx_pad_sample fx_samples[2];
static PadState sd_keyboard_pad;
static int fx_keyboard_ready,fx_keyboard_applet_active,fx_game_active,sd_keyboard_disconnected;
static unsigned fx_players=1;
static pthread_t sd_keyboard_thread;
static int sd_keyboard_created,sd_keyboard_stop;
static void fx_keyboard_poll_locked(void);
int fx_pads_paused(void){return __atomic_load_n(&sd_keyboard_disconnected,__ATOMIC_ACQUIRE);}
unsigned fx_pads_players(void){return 1;}
void fx_pads_snapshot(struct fx_pad_sample out[2]){
    pthread_mutex_lock(&fx_pad_lock);
    if(!__atomic_load_n(&fx_keyboard_applet_active,__ATOMIC_ACQUIRE)){
        padUpdate(&sd_keyboard_pad);
        HidAnalogStickState l=padGetStickPos(&sd_keyboard_pad,0),r=padGetStickPos(&sd_keyboard_pad,1);
        int connected=padIsConnected(&sd_keyboard_pad);u32 style=padGetStyleSet(&sd_keyboard_pad);
        int kind=style&HidNpadStyleTag_NpadHandheld?FX_PAD_HANDHELD:
            style==HidNpadStyleTag_NpadJoyLeft?FX_PAD_LEFT:style==HidNpadStyleTag_NpadJoyRight?FX_PAD_RIGHT:FX_PAD_FULL;
        fx_pad_update(&fx_samples[0],fx_pad_normalize(kind,connected,padGetButtons(&sd_keyboard_pad),l.x,l.y,r.x,r.y));
        __atomic_store_n(&sd_keyboard_disconnected,!connected,__ATOMIC_RELEASE);
        fx_keyboard_poll_locked();
    }
    out[0]=fx_samples[0];out[1]=fx_samples[1];pthread_mutex_unlock(&fx_pad_lock);
}
#define FX_OSK_TRACE(...) log_line(__VA_ARGS__)
#include "fextendo_keyboard_switch.h"
#include "pes13/fextendo_osk_display.h"
#include "pes13/fextendo_osk_switch.h"
#include "pes13/fextendo_keyboard_capture.h"
void sd_keyboard_present_gate(void){
    if(!__atomic_load_n(&fx_keyboard_applet_active,__ATOMIC_ACQUIRE))return;
    pthread_mutex_lock(&fx_pad_lock);
    while(__atomic_load_n(&fx_keyboard_applet_active,__ATOMIC_ACQUIRE))pthread_cond_wait(&fx_pad_cond,&fx_pad_lock);
    pthread_mutex_unlock(&fx_pad_lock);
}
static void *sd_keyboard_monitor(void *unused){
    (void)unused;fx_keyboard_capture_start();
    while(!__atomic_load_n(&sd_keyboard_stop,__ATOMIC_ACQUIRE)){
        if(!appletMainLoop())break;
        struct fx_pad_sample pads[2];fx_pads_snapshot(pads);
        if(fx_pads_paused())fx_keyboard_cancel_all();
        fx_keyboard_capture_poll();fx_keyboard_service();fx_osk_service();
        svcSleepThread(20000000);
    }
    fx_keyboard_capture_stop();fx_keyboard_cancel_all();fx_osk_abort(0);fx_osk_display_close();return NULL;
}
static void sd_keyboard_shutdown(void){
    __atomic_store_n(&sd_keyboard_stop,1,__ATOMIC_RELEASE);
    if(sd_keyboard_created){pthread_join(sd_keyboard_thread,NULL);sd_keyboard_created=0;}
}
static int sd_keyboard_start(void){
    padInitializeDefault(&sd_keyboard_pad);hidInitializeTouchScreen();
    fx_game_active=1;__atomic_store_n(&fx_keyboard_ready,1,__ATOMIC_RELEASE);
    pthread_attr_t attr;int rc=pthread_attr_init(&attr);if(rc)return 0;
    rc=pthread_attr_setstacksize(&attr,128*1024);
    if(!rc)rc=pthread_create(&sd_keyboard_thread,&attr,sd_keyboard_monitor,NULL);
    pthread_attr_destroy(&attr);
    if(rc){__atomic_store_n(&fx_keyboard_ready,0,__ATOMIC_RELEASE);return 0;}
    sd_keyboard_created=1;atexit(sd_keyboard_shutdown);
    log_line("[SD-KEYBOARD] launcher-v1 PES13 38750c20; shortcut=%d hold_ms=%d top=%d; native + Wine Vulkan",fx_keyboard_options.shortcut,fx_keyboard_options.hold_ms,fx_keyboard_options.top);
    return 1;
}
