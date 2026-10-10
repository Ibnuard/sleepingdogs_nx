"""Exercise the actual Horizon destroy-window handler and reproduce the old fault.

Runs the generated C handler with real allocation and list objects under ASan/
UBSan; external clipboard/queue/IPC services are mocked. No Switch is simulated.
"""
from pathlib import Path
import argparse
import re
import shutil
import subprocess
from check_startup import function

MOCK = r'''
#include <assert.h>
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <pthread.h>
#define HORIZON_STATUS_SUCCESS 0u
#define HORIZON_STATUS_INVALID_HANDLE 0xc0000008u
struct horizon_server_connection {int reply_fd;unsigned int pid,tid;};
struct horizon_input_shm {unsigned int caret;};
static struct horizon_user_window *horizon_windows;
static pthread_mutex_t horizon_server_objects_mutex=PTHREAD_MUTEX_INITIALIZER;
static struct horizon_input_shm input;
static int horizon_posted_messages,horizon_timers,horizon_clipboard;
static unsigned int dropped[16],timers[16],clip_events[16],drops,timer_drops,clip_calls;
static unsigned int clip_owner,notifies,caret_clears,flushes,refreshes,replies,last_status;
static void check_locked(void){assert(pthread_mutex_trylock(&horizon_server_objects_mutex)!=0);}
static void horizon_message_queue_drop(int *q,unsigned int tid,unsigned int hwnd){check_locked();assert(q==&horizon_posted_messages&&tid);dropped[drops++]=hwnd;}
static void horizon_win_timers_drop(int *q,unsigned int tid,unsigned int hwnd){check_locked();assert(q==&horizon_timers&&tid);timers[timer_drops++]=hwnd;}
static int horizon_clip_window_destroyed(int *q,unsigned int hwnd){check_locked();assert(q==&horizon_clipboard);clip_events[clip_calls++]=hwnd;return hwnd==clip_owner;}
static void horizon_server_clipboard_notify_locked(void){check_locked();++notifies;}
static struct horizon_input_shm *horizon_server_input_shared_locked(void){check_locked();return &input;}
static void horizon_server_set_caret_window_locked(struct horizon_input_shm *i,unsigned int hwnd,int x,int y){check_locked();assert(i==&input&&!hwnd&&!x&&!y);input.caret=0;++caret_clears;}
static void horizon_server_flush_input_locked(void){check_locked();++flushes;}
static void horizon_server_refresh_queues_locked(void){check_locked();++refreshes;}
static int horizon_server_write_status(int fd,unsigned int status){assert(fd==77);assert(!pthread_mutex_trylock(&horizon_server_objects_mutex));pthread_mutex_unlock(&horizon_server_objects_mutex);++replies;last_status=status;return 123;}
'''

TEST = r'''
static struct horizon_server_connection connection={77,7,92};
static void reset(void){
 assert(!horizon_windows);drops=timer_drops=clip_calls=notifies=caret_clears=flushes=refreshes=replies=0;
 clip_owner=input.caret=0;
}
static struct horizon_user_window *add(unsigned handle,unsigned owner){
 struct horizon_user_window *w=calloc(1,sizeof(*w));assert(w);
 w->handle=handle;w->pid=owner==2?9:7;w->tid=owner==1?4:92;
 w->style=0x15000000;w->window_rect.right=1280;w->window_rect.bottom=720;
 for(unsigned i=0;i<2;i++){struct horizon_window_property *p=calloc(1,sizeof(*p));assert(p);p->next=w->properties;w->properties=p;}
 struct horizon_user_window **tail=&horizon_windows;while(*tail)tail=&(*tail)->next;*tail=w;
 return w;
}
static void clear(void){
 while(horizon_windows){struct horizon_user_window *w=horizon_windows;horizon_windows=w->next;
 while(w->properties){struct horizon_window_property *p=w->properties;w->properties=p->next;free(p);}free(w);}
}
static void request(unsigned handle){
 struct horizon_destroy_window_request r={.handle=handle};
 assert(horizon_server_handle_destroy_window(&connection,(const unsigned char*)&r)==123);
 assert(refreshes==1&&replies==1);
}
static void check_effects(const unsigned *removed,unsigned count,unsigned caret){
 assert(drops==count&&timer_drops==count&&clip_calls==count);
 assert(!memcmp(dropped,removed,count*sizeof(unsigned)));
 assert(!memcmp(timers,removed,count*sizeof(unsigned)));
 assert(!memcmp(clip_events,removed,count*sizeof(unsigned)));
 unsigned expected_clear=0;for(unsigned i=0;i<count;i++)if(removed[i]==caret)expected_clear=1;
 assert(caret_clears==expected_clear&&flushes==expected_clear&&notifies==expected_clear);
 assert(input.caret==(expected_clear?0:caret));
}
int main(int argc,char **argv){
 /* The device instruction loads window->next at NULL + 0xd0. Keep the real
  * server struct layout so this regression reproduces that exact address. */
 _Static_assert(offsetof(struct horizon_user_window,next)==0xd0,"window ABI changed");
 if(argc>1){reset();add(0x20042,0);request(0);clear();return 0;}
 unsigned cases=0;
 for(unsigned n=0,patterns=1;n<=6;n++,patterns*=3){
  for(unsigned pattern=0;pattern<patterns;pattern++){
   reset();unsigned p=pattern,removed[6],count=0,kept_count=0;
   struct horizon_user_window *kept[6];
   for(unsigned i=0;i<n;i++){
    unsigned owner=p%3;p/=3;struct horizon_user_window *w=add(0x10040+i,owner);
    if(!owner)removed[count++]=w->handle;else kept[kept_count++]=w;
   }
   unsigned caret=n?0x10040+n-1:0;input.caret=clip_owner=caret;
   request(0);assert(last_status==HORIZON_STATUS_SUCCESS);
   struct horizon_user_window *w=horizon_windows;
   for(unsigned i=0;i<kept_count;i++){assert(w==kept[i]&&w->style==0x15000000&&w->window_rect.right==1280);w=w->next;}
   assert(!w);check_effects(removed,count,caret);clear();++cases;
  }
 }
 /* Single-window requests retain their previous explicit-handle semantics. */
 for(unsigned target=0;target<6;target++){
  reset();struct horizon_user_window *kept[5];unsigned count=0;
  for(unsigned i=0;i<5;i++){struct horizon_user_window *w=add(0x10040+i,i%3);if(i!=target)kept[count++]=w;}
  unsigned hwnd=0x10040+target;input.caret=clip_owner=hwnd;
  request(hwnd);assert(last_status==(target<5?HORIZON_STATUS_SUCCESS:HORIZON_STATUS_INVALID_HANDLE));
  struct horizon_user_window *w=horizon_windows;for(unsigned i=0;i<count;i++){assert(w==kept[i]);w=w->next;}assert(!w);
  check_effects(&hwnd,target<5?1:0,hwnd);clear();++cases;
 }
 reset();request(0x99999);assert(last_status==HORIZON_STATUS_INVALID_HANDLE);++cases;
 printf("PASS: actual destroy-window handler, %u cases; empty/singleton/head/middle/tail/adjacent nodes, PID+TID ownership, explicit handles, properties, queues, timers, clipboard, caret, mutex and IPC reply\n",cases);
}
'''

def struct(source,name):
    match=re.search(r'struct '+name+r'\n\{[\s\S]*?\n\};',source)
    assert match,name
    return match[0]+'\n'

def compile_handler(source,output,name):
    text=source.read_text()
    structs=''.join(struct(text,name) for name in ('horizon_rectangle','horizon_obj_locator',
        'horizon_server_request_header','horizon_window_property','horizon_user_window','horizon_destroy_window_request'))
    handler=function(text,'static int horizon_server_handle_destroy_window(')
    c=output/(name+'.c');exe=output/name
    c.write_text(MOCK+structs+handler+TEST)
    subprocess.run([shutil.which('cc'),'-std=gnu11','-O1','-g','-pthread',
                    '-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer',
                    str(c),'-o',str(exe)],check=True)
    return exe

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--baseline',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    relative='dlls/ntdll/unix/horizon.c'
    baseline=compile_handler(a.baseline/relative,a.output,'baseline')
    result=subprocess.run([str(baseline),'singleton'],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    (a.output/'baseline-failure.log').write_text(result.stdout)
    assert result.returncode and ('null pointer' in result.stdout or '0x0000000000d0' in result.stdout),result.stdout
    print('PASS: shipped 0.1.12 handler reproduces the NULL+0xd0 list-advance fault under sanitizers',flush=True)
    current=compile_handler(a.source/relative,a.output,'fixed')
    subprocess.run([str(current)],check=True)

if __name__=='__main__':main()
