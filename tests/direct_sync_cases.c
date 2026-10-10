/* Cases run on real handlers above; platform object lookup is the fixture. */
static unsigned call(unsigned tid, const void *req, const void *data, unsigned size, void *reply, void *extra) {
    assert(horizon_server_sync_call(tid, req, data, size, reply, extra));
    assert(!horizon_server_current);
    return ((struct horizon_server_reply_header *)reply)->error;
}
static unsigned event(unsigned tid, unsigned h, unsigned op) {
    struct horizon_event_op_request r = { .header.req = HORIZON_REQ_EVENT_OP, .handle = h, .op = op };
    unsigned char reply[HORIZON_SERVER_FIXED_MESSAGE_SIZE]; return call(tid, &r, NULL, 0, reply, NULL);
}
static unsigned select_op(unsigned tid, unsigned op, unsigned h, unsigned second, int two, long long timeout, int alertable, int legacy) {
    struct horizon_select_request r = { .header = { .req = HORIZON_REQ_SELECT, .reply_size = HORIZON_APC_CALL_SIZE },
        .flags = alertable ? SELECT_ALERTABLE : 0, .timeout = timeout, .size = two ? 12 : 8 };
    struct { unsigned char apc[HORIZON_APC_RESULT_SIZE]; unsigned op, handles[2]; } d = { .op = op, .handles = {h, second} };
    unsigned char reply[HORIZON_SERVER_FIXED_MESSAGE_SIZE], extra[HORIZON_APC_CALL_SIZE];
    r.header.request_size = HORIZON_APC_RESULT_SIZE + r.size;
    if (!legacy) return call(tid, &r, &d, r.header.request_size, reply, extra);
    struct horizon_server_connection c = { .tid = tid, .thread = &threads[tid-1] };
    horizon_server_current = &c;
    assert(!horizon_server_handle_select(&c, (const void *)&r, (const void *)&d, r.header.request_size));
    horizon_server_current = NULL;
    return ((struct horizon_server_reply_header *)pipe_reply)->error;
}
static unsigned wait_for(unsigned tid, unsigned h, long long timeout) {
    return select_op(tid, HORIZON_SELECT_WAIT, h, 0, 0, timeout, 0, 0);
}
static unsigned release_mutex(unsigned tid, unsigned h) {
    struct horizon_release_mutex_request r = { .header.req = HORIZON_REQ_RELEASE_MUTEX, .handle = h };
    unsigned char reply[HORIZON_SERVER_FIXED_MESSAGE_SIZE]; return call(tid, &r, NULL, 0, reply, NULL);
}
static unsigned release_sem(unsigned tid, unsigned h, unsigned count) {
    struct horizon_release_semaphore_request r = { .header.req = HORIZON_REQ_RELEASE_SEMAPHORE, .handle = h, .count = count };
    unsigned char reply[HORIZON_SERVER_FIXED_MESSAGE_SIZE]; return call(tid, &r, NULL, 0, reply, NULL);
}
struct job { unsigned tid, op, h, second, status; int two, alertable, legacy; };
static void *wait_job(void *p) {
    struct job *j = p;
    j->status = select_op(j->tid, j->op, j->h, j->second, j->two,
                         -(clock_ticks() + 30000000), j->alertable, j->legacy);
    return NULL;
}
static void wait_queued(unsigned n, int legacy) {
    long long deadline = clock_ticks() + 20000000;
    for (;;) {
        pthread_mutex_lock(&horizon_server_objects_mutex);
        unsigned seen = legacy ? horizon_server_sleepers : sd_sync_counts[6];
        pthread_mutex_unlock(&horizon_server_objects_mutex);
        if (seen == n) break;
        assert(clock_ticks() < deadline); usleep(100);
    }
}
static void join(pthread_t t, struct job *j, unsigned status) {
    assert(!pthread_join(t, NULL)); assert(j->status == status);
    assert(threads[j->tid-1].refs == 1);
}
static void clear_events(void) { for (unsigned h=1; h<=3; ++h) assert(!event(1,h,HORIZON_RESET_EVENT)); }
static void *ping_worker(void *p) {
    int loops = *(int *)p;
    for (int i=0;i<loops;++i) {
        assert(!wait_for(2,1,-(clock_ticks()+20000000)));
        assert(!event(2,2,HORIZON_SET_EVENT));
    }
    return NULL;
}
int main(void) {
    for (unsigned i=0;i<8;++i) {
        threads[i].refs=1; threads[i].thread.tid=i+1; threads[i].thread.pid=1; threads[i].thread.started=1;
        threads[i].thread_next=i<7 ? threads+i+1 : NULL;
    }
    for (unsigned i=1;i<16;++i) { objects[i].type=HORIZON_SERVER_OBJECT_EVENT; objects[i].refs=1; handles[i].object=objects+i; }
    objects[4].type=HORIZON_SERVER_OBJECT_MUTEX;
    objects[5].type=HORIZON_SERVER_OBJECT_SEMAPHORE; objects[5].max=2;
    objects[6].type=HORIZON_SERVER_OBJECT_TIMER; objects[6].timer_when=1;
    struct horizon_event_op_request r = { .header.req=HORIZON_REQ_EVENT_OP, .handle=1, .op=HORIZON_SET_EVENT };
    unsigned char reply[HORIZON_SERVER_FIXED_MESSAGE_SIZE];
    assert(!horizon_server_sync_call(1,&r,NULL,0,reply,NULL));
    horizon_fast_sync_enabled=2;
    assert(!horizon_server_sync_call(99,&r,NULL,0,reply,NULL));
    threads[0].thread.started=0; assert(!horizon_server_sync_call(1,&r,NULL,0,reply,NULL)); threads[0].thread.started=1;
    threads[0].thread.suspend=1; assert(!horizon_server_sync_call(1,&r,NULL,0,reply,NULL)); threads[0].thread.suspend=0;
    threads[0].thread.terminated=1; assert(!horizon_server_sync_call(1,&r,NULL,0,reply,NULL)); threads[0].thread.terminated=0;
    r.header.request_size=1; assert(!horizon_server_sync_call(1,&r,NULL,0,reply,NULL)); r.header.request_size=0;
    r.header.reply_size=1; assert(!horizon_server_sync_call(1,&r,NULL,0,reply,NULL)); r.header.reply_size=0;
    r.header.req=0x7fffffff; assert(!horizon_server_sync_call(1,&r,NULL,0,reply,NULL));
    puts("PASS modes/dispatch: off, unknown thread, startup, suspend, terminated, payload, unsupported fallback");
    for (int mode=1;mode<=2;++mode) {
        horizon_fast_sync_enabled=mode;
        assert(!event(1,1,HORIZON_SET_EVENT)); assert(!wait_for(1,1,0)); assert(wait_for(1,1,0)==HORIZON_STATUS_TIMEOUT);
        objects[1].manual_reset=1; assert(!event(1,1,HORIZON_SET_EVENT)); assert(!wait_for(1,1,0)); assert(!wait_for(1,1,0));
        assert(!event(1,1,HORIZON_RESET_EVENT)); objects[1].manual_reset=0;
        assert(event(1,4,HORIZON_SET_EVENT)==HORIZON_STATUS_OBJECT_TYPE_MISMATCH);
        assert(event(1,99,HORIZON_SET_EVENT)==HORIZON_STATUS_INVALID_HANDLE);
        assert(!wait_for(1,4,0)); assert(!wait_for(1,4,0)); assert(objects[4].mutex.count==2);
        assert(release_mutex(2,4)==HORIZON_THREADS_STATUS_MUTANT_NOT_OWNED);
        assert(!release_mutex(1,4)); assert(!release_mutex(1,4));
        objects[4].mutex.abandoned=1; assert(wait_for(1,4,0)==HORIZON_STATUS_ABANDONED_WAIT_0); assert(!release_mutex(1,4));
        assert(!release_sem(1,5,2)); assert(release_sem(1,5,1)==HORIZON_STATUS_SEMAPHORE_LIMIT_EXCEEDED);
        assert(!wait_for(1,5,0)); assert(!wait_for(1,5,0)); assert(wait_for(1,5,0)==HORIZON_STATUS_TIMEOUT);
        long long start=clock_ticks(); assert(wait_for(1,1,-(start+60000))==HORIZON_STATUS_TIMEOUT); assert(clock_ticks()-start>=60000);
        assert(wait_for(1,6,-(clock_ticks()+20000))==HORIZON_STATUS_TIMEOUT);
        assert(!event(1,2,HORIZON_SET_EVENT));
        assert(select_op(1,HORIZON_SELECT_WAIT,1,2,1,0,0,0)==1);
        assert(!event(1,1,HORIZON_SET_EVENT));
        assert(select_op(1,HORIZON_SELECT_WAIT_ALL,1,2,1,0,0,0)==HORIZON_STATUS_TIMEOUT); assert(objects[1].signaled);
        assert(!event(1,2,HORIZON_SET_EVENT)); assert(!select_op(1,HORIZON_SELECT_WAIT_ALL,1,2,1,0,0,0));
        assert(!objects[1].signaled && !objects[2].signaled);
        assert(!event(1,1,HORIZON_SET_EVENT));
        assert(!select_op(1,HORIZON_SELECT_SIGNAL_AND_WAIT,1,2,1,0,0,0)); assert(objects[2].signaled);
        assert(!event(1,2,HORIZON_RESET_EVENT)); assert(!event(1,1,HORIZON_SET_EVENT));
        assert(!select_op(1,HORIZON_SELECT_SIGNAL_AND_WAIT,1,0,0,0,0,0)); assert(!objects[2].signaled);
    }
    puts("PASS direct modes 1/2: events, recursive/abandoned mutex, semaphores, wait-any/all, signal-and-wait retry, deadlines, timer fallback");
    clear_events();
    pthread_t t, t2;
    struct job j={.tid=2,.op=HORIZON_SELECT_WAIT,.h=1};
    assert(!pthread_create(&t,NULL,wait_job,&j)); wait_queued(1,0);
    pthread_mutex_lock(&horizon_server_objects_mutex);
    uint64_t notified=sd_sync_counts[1];
    objects[3].signaled=1; fex_sync_signal_object_locked(objects+3); assert(sd_sync_counts[1]==notified);
    objects[1].signaled=1; fex_sync_signal_object_locked(objects+1);
    assert(sd_sync_counts[1]==notified+1 && !objects[1].signaled);
    objects[1].signaled=0; /* Reset before the waiter can reacquire the lock. */
    pthread_mutex_unlock(&horizon_server_objects_mutex);
    join(t,&j,0); assert(!sd_sync_counts[6]);
    puts("PASS targeted wake ignores unrelated object; committed auto-event survives immediate reset");
    clear_events(); objects[1].manual_reset=1;
    struct job j2={.tid=3,.op=HORIZON_SELECT_WAIT,.h=1};
    assert(!pthread_create(&t,NULL,wait_job,&j)); assert(!pthread_create(&t2,NULL,wait_job,&j2)); wait_queued(2,0);
    assert(!event(1,1,HORIZON_SET_EVENT)); join(t,&j,0); join(t2,&j2,0); objects[1].manual_reset=0; clear_events();
    j.two=1; j.second=2; j.op=HORIZON_SELECT_WAIT_ALL;
    assert(!pthread_create(&t,NULL,wait_job,&j)); wait_queued(1,0);
    assert(!event(1,1,HORIZON_SET_EVENT)); assert(!event(1,2,HORIZON_SET_EVENT)); join(t,&j,0);
    assert(!objects[1].signaled && !objects[2].signaled);
    j.two=0; j.op=HORIZON_SELECT_WAIT;
    puts("PASS manual-event wakes all and queued wait-all consumes only complete set");
    j.legacy=1; assert(!pthread_create(&t,NULL,wait_job,&j)); wait_queued(1,1);
    assert(!event(1,1,HORIZON_SET_EVENT)); join(t,&j,0); j.legacy=0;
    assert(!pthread_create(&t,NULL,wait_job,&j)); wait_queued(1,0);
    pthread_mutex_lock(&horizon_server_objects_mutex);
    assert(objects[1].refs==2); handles[1].object=NULL; sd_sync_notify_locked(objects+1);
    assert(--objects[1].refs==1); pthread_mutex_unlock(&horizon_server_objects_mutex);
    join(t,&j,HORIZON_STATUS_INVALID_HANDLE); assert(freed_objects==1);
    handles[1].object=objects+1; objects[1].refs=1;
    puts("PASS legacy wait receives direct signal; queued reference survives handle close");
    j.alertable=1; assert(!pthread_create(&t,NULL,wait_job,&j)); wait_queued(1,0);
    pthread_mutex_lock(&horizon_server_objects_mutex);
    struct user_apc apc={.type=1,.func=0x1234}; assert(!f1_apc_push(&threads[1].f1_apcs,&apc));
    horizon_server_signal_changed_locked(); pthread_mutex_unlock(&horizon_server_objects_mutex);
    join(t,&j,STATUS_USER_APC); assert(f1_apc_delivered==1); j.alertable=0;
    puts("PASS original user-APC queue wakes alertable direct waiter and releases queue/TLS references");
    /* The notifying thread must not become the owner of another thread's mutex. */
    assert(!wait_for(1,4,0)); j.h=4;
    assert(!pthread_create(&t,NULL,wait_job,&j)); wait_queued(1,0);
    assert(!release_mutex(1,4)); join(t,&j,0);
    assert(objects[4].mutex.owner==2 && objects[4].mutex.count==1);
    assert(!release_mutex(2,4));
    /* Each semaphore token may satisfy one queued waiter, never both. */
    j.h=5; j2.h=5;
    assert(!pthread_create(&t,NULL,wait_job,&j)); assert(!pthread_create(&t2,NULL,wait_job,&j2)); wait_queued(2,0);
    pthread_mutex_lock(&horizon_server_objects_mutex); uint64_t completed=sd_sync_counts[3]; pthread_mutex_unlock(&horizon_server_objects_mutex);
    assert(!release_sem(1,5,1));
    pthread_mutex_lock(&horizon_server_objects_mutex); assert(sd_sync_counts[3]==completed+1 && !objects[5].count); pthread_mutex_unlock(&horizon_server_objects_mutex);
    assert(!release_sem(1,5,1)); join(t,&j,0); join(t2,&j2,0);
    objects[7].type=HORIZON_SERVER_OBJECT_THREAD; j.h=7;
    assert(!pthread_create(&t,NULL,wait_job,&j)); wait_queued(1,0);
    pthread_mutex_lock(&horizon_server_objects_mutex); objects[7].thread.terminated=1; horizon_server_signal_changed_locked(); pthread_mutex_unlock(&horizon_server_objects_mutex);
    join(t,&j,0); objects[7].type=HORIZON_SERVER_OBJECT_EVENT;
    pthread_mutex_lock(&horizon_server_objects_mutex); assert(!f1_apc_push(&threads[0].f1_apcs,&apc)); pthread_mutex_unlock(&horizon_server_objects_mutex);
    assert(!event(1,1,HORIZON_SET_EVENT));
    assert(!select_op(1,HORIZON_SELECT_WAIT,1,0,0,0,1,0)); assert(threads[0].f1_apcs.head);
    assert(select_op(1,HORIZON_SELECT_WAIT,1,0,0,0,1,0)==STATUS_USER_APC); assert(!threads[0].f1_apcs.head);
    puts("PASS queued mutex uses waiter identity; one semaphore token wakes one waiter; thread termination and object-before-APC ordering");
    clear_events(); int loops=3000;
    assert(!pthread_create(&t,NULL,ping_worker,&loops));
    for (int i=0;i<loops;++i) { assert(!event(1,1,HORIZON_SET_EVENT)); assert(!wait_for(1,2,-(clock_ticks()+20000000))); }
    assert(!pthread_join(t,NULL)); assert(!sd_sync_waiters && !sd_sync_counts[6]);
    for (unsigned i=1;i<16;++i) assert(objects[i].refs==1 && !objects[i].sd_waiters);
    assert(threads[1].refs==1);
    puts("PASS 3000 threaded event round trips: no lost signals, leaked object references or queued waiters");
    assert(sd_sync_parse_mode("2\n",2)==2 && sd_sync_parse_mode("1\r\n",3)==1);
    assert(!sd_sync_parse_mode("9",1) && !sd_sync_parse_mode("2x",2) && !sd_sync_parse_mode("2\n\n",3));
    assert(!sd_sync_load_mode("/does/not/exist"));
    puts("PASS sync-mode parser: valid modes, missing/invalid file returns original server mode");
    return 0;
}
