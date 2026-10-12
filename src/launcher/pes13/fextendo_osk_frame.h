/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Native OSK pixels shared with the game's presenter, as in Autorun's osk.h.
 * A snapshot identifies both the session and its exact geometry/content.
 */
#ifndef FEXTENDO_OSK_FRAME_H
#define FEXTENDO_OSK_FRAME_H
#include <stdint.h>
struct fx_osk_frame {
    int x, y, width, height;
    uint64_t session, generation;
};
int fx_osk_frame_visible(void);
int fx_osk_frame_get(int screen_w,int screen_h,struct fx_osk_frame *frame);
int fx_osk_frame_copy(const struct fx_osk_frame *frame,void *pixels,int stride,int rgba);
void fx_osk_frame_presented(uint64_t session);
void fx_osk_frame_reject(uint64_t session);
#endif
