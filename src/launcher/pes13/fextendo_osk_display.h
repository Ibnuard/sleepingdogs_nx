/* SPDX-License-Identifier: LGPL-2.1-or-later
 * The monitor publishes CPU pixels. Vulkan copies them into the game image,
 * following Autorun's in-frame OSK approach, without a separate VI layer.
 * The presenter never takes the input mutex or performs SD I/O.
 */
#include "fextendo_osk_ui.h"
#include "fextendo_osk_frame.h"
#ifndef FX_OSK_TRACE
#ifdef FX_SCREEN_DEBUG
#define FX_OSK_TRACE(...) fx_launch_debug_log(__VA_ARGS__)
#else
#define FX_OSK_TRACE(...) ((void)0)
#endif
#endif
static pthread_mutex_t fx_osk_pixels_lock=PTHREAD_MUTEX_INITIALIZER;
static struct fx_art fx_osk_art;
static uint32_t *fx_osk_pixels;
static unsigned fx_osk_drawn_generation;
static int fx_osk_pixels_visible,fx_osk_pixels_top,fx_osk_pixels_single,fx_osk_pixels_failed;
static uint64_t fx_osk_pixels_session,fx_osk_pixels_generation,fx_osk_pixels_started,fx_osk_pixels_seen;
static uint64_t fx_osk_display_ms(void){return armGetSystemTick()/(armGetSystemTickFreq()/1000);}

int fx_osk_frame_visible(void){return __atomic_load_n(&fx_osk_pixels_visible,__ATOMIC_ACQUIRE);}
int fx_osk_frame_get(int sw,int sh,struct fx_osk_frame *f){
    if(!fx_osk_frame_visible()||!f||sw<1||sh<3||sw>8192||sh>8192)return 0;
    pthread_mutex_lock(&fx_osk_pixels_lock);
    int ok=fx_osk_pixels_visible&&!fx_osk_pixels_failed;
    if(ok){
        f->x=0;f->width=sw;f->height=sh*FX_OSK_HEIGHT/FX_H;
        f->y=fx_osk_pixels_top?0:sh-f->height;
        f->session=fx_osk_pixels_session;f->generation=fx_osk_pixels_generation;
    }
    pthread_mutex_unlock(&fx_osk_pixels_lock);return ok;
}
int fx_osk_frame_copy(const struct fx_osk_frame *f,void *pixels,int stride,int rgba){
    if(!f||!pixels||f->width<1||f->height<1||f->width>8192||f->height>8192||stride<f->width*4)return 0;
    pthread_mutex_lock(&fx_osk_pixels_lock);
    int ok=fx_osk_pixels_visible&&!fx_osk_pixels_failed&&f->session==fx_osk_pixels_session&&f->generation==fx_osk_pixels_generation;
    if(ok)for(int y=0;y<f->height;y++){
        uint32_t *dst=(uint32_t *)((unsigned char *)pixels+(size_t)y*stride);
        const uint32_t *src=fx_osk_pixels+(size_t)(y*FX_OSK_HEIGHT/f->height)*FX_W;
        if(rgba&&f->width==FX_W)memcpy(dst,src,FX_W*4);
        else for(int x=0;x<f->width;x++){
            uint32_t c=src[x*FX_W/f->width];
            dst[x]=rgba?c:(c&0xff00ff00u)|((c&255)<<16)|((c>>16)&255);
        }
    }
    pthread_mutex_unlock(&fx_osk_pixels_lock);return ok;
}
void fx_osk_frame_presented(uint64_t session){
    pthread_mutex_lock(&fx_osk_pixels_lock);
    if(fx_osk_pixels_visible&&session==fx_osk_pixels_session)fx_osk_pixels_seen=fx_osk_display_ms();
    pthread_mutex_unlock(&fx_osk_pixels_lock);
}
void fx_osk_frame_reject(uint64_t session){
    pthread_mutex_lock(&fx_osk_pixels_lock);
    if(fx_osk_pixels_visible&&session==fx_osk_pixels_session)fx_osk_pixels_failed=1;
    pthread_mutex_unlock(&fx_osk_pixels_lock);
}
static __attribute__((noinline,noclone)) void fx_osk_display_close(void){
    pthread_mutex_lock(&fx_osk_pixels_lock);
    __atomic_store_n(&fx_osk_pixels_visible,0,__ATOMIC_RELEASE);
    free(fx_osk_pixels);fx_osk_pixels=NULL;fx_osk_drawn_generation=0;
    fx_osk_pixels_failed=0;fx_osk_pixels_seen=0;
    pthread_mutex_unlock(&fx_osk_pixels_lock);
    fx_art_free(&fx_osk_art);
}
/* 0 = failure, 1 = actually presented, 2 = waiting for the first game frame.
 * Never start typing into an invisible overlay. No-present timeout also
 * restores control when the game is not using our supported presenter. */
static __attribute__((noinline,noclone)) int fx_osk_display_show(const struct fx_osk_core *state,unsigned player,int single){
    int first=!fx_osk_pixels;
    if(first){
        if(!fx_font_load(&fx_osk_art,RUNTIME_DIR))goto failed;
        fx_osk_pixels=malloc((size_t)FX_W*FX_OSK_HEIGHT*4);
        if(!fx_osk_pixels)goto failed;
    }
    pthread_mutex_lock(&fx_osk_pixels_lock);
    if(first){
        if(!++fx_osk_pixels_session)++fx_osk_pixels_session;
        fx_osk_pixels_started=fx_osk_display_ms();fx_osk_pixels_seen=0;fx_osk_pixels_failed=0;
    }
    if(first||fx_osk_drawn_generation!=state->generation||fx_osk_pixels_single!=single){
        struct fx_canvas canvas={.pixels=fx_osk_pixels,.stride=FX_W,.art=&fx_osk_art,.clip_bottom=FX_OSK_HEIGHT};
        fx_osk_draw(&canvas,state,player,single);
        fx_osk_drawn_generation=state->generation;fx_osk_pixels_top=state->top;fx_osk_pixels_single=single;
        if(!++fx_osk_pixels_generation)++fx_osk_pixels_generation;
        __atomic_store_n(&fx_osk_pixels_visible,1,__ATOMIC_RELEASE);
    }
    int failed=fx_osk_pixels_failed||fx_osk_display_ms()-(fx_osk_pixels_seen?fx_osk_pixels_seen:fx_osk_pixels_started)>3000;
    int status=failed?0:fx_osk_pixels_seen?1:2;
    pthread_mutex_unlock(&fx_osk_pixels_lock);
    if(first)FX_OSK_TRACE("[OSK] frame published player=%u session=%llu",player+1,(unsigned long long)fx_osk_pixels_session);
    if(!status)goto failed;
    return status;
failed:
    FX_OSK_TRACE("[OSK] frame unavailable; restore game input");
    fx_osk_display_close();return 0;
}
static int fx_osk_touch(int *x,int *y){
    HidTouchScreenState touch;
    if(!hidGetTouchScreenStates(&touch,1)||!touch.count)return 0;
    *x=touch.touches[0].x;*y=touch.touches[0].y;return 1;
}
