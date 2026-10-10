/* Production notifier/APC enqueue/select handlers; real pthread condvars. */
static unsigned v18_queue(unsigned handle, unsigned kind, unsigned flags,
                          unsigned reserve, uint64_t callback, unsigned bytes)
{
    struct horizon_server_connection c = {.tid=1, .thread=threads};
    struct queue_apc_request r = {.handle=handle, .reserve_handle=reserve};
    union apc_call call = {.user={.type=kind, .flags=flags, .func=callback}};
    assert(!f1_server_queue_apc(&c, (const void *)&r, (const void *)&call, bytes));
    return ((struct queue_apc_reply *)pipe_reply)->__header.error;
}

static void v18_helper_matrix(void)
{
    unsigned cases=0;
    for (int enabled=0; enabled<=1; ++enabled)
    for (int mode=0; mode<=2; ++mode)
    for (int routed=0; routed<=1; ++routed)
    for (int pending=0; pending<=1; ++pending)
    for (int target_kind=0; target_kind<3; ++target_kind) {
        struct horizon_server_connection c[3]={{.thread=threads+1},{.thread=threads+2},{.thread=threads+1}};
        struct horizon_select_request requests[3]={{.flags=SELECT_ALERTABLE},{0},{0}};
        struct sd_sync_waiter w[3] = {
            {.connection=c, .request=requests, .condition=PTHREAD_COND_INITIALIZER},
            {.connection=c+1, .request=requests+1, .condition=PTHREAD_COND_INITIALIZER},
            {.connection=c+2, .request=requests+2, .condition=PTHREAD_COND_INITIALIZER}};
        pthread_cond_t legacy=PTHREAD_COND_INITIALIZER;
        struct pes27_waiter lw={.condition=&legacy};
        const struct horizon_server_object *target = target_kind==0 ? threads+1 : target_kind==1 ? threads+3 : NULL;
        const int filtered=enabled && mode==2 && target;
        w[0].next=w+1; w[1].next=w+2;
        w[0].notified=pending;
        w[2].completed=1; w[2].status=0x1234; /* no completion/state mutation */
        pthread_mutex_lock(&horizon_server_objects_mutex);
        assert(!sd_sync_waiters && !horizon_server_sleepers);
        sd_sync_waiters=w; horizon_server_sleepers=1;
        wine_nx_sd_apc_targeted_wake=enabled; horizon_fast_sync_enabled=mode;
        wine_nx_fex_targeted_wake=routed;
        pes27_register(&fex_sync_router,&lw);
        uint64_t old[4]; memcpy(old,sd_apc_notify_counts,sizeof(old));
        uint64_t legacy_before=fex_sync_router.broad_notices;
        unsigned signals=observed_signals, broadcasts=observed_broadcasts;
        sd_sync_signal_apc_locked(target);
        assert(sd_apc_notify_counts[0]==old[0]+1);
        assert(sd_apc_notify_counts[1]==old[1]+(filtered && !target_kind ? 2 : 0));
        assert(sd_apc_notify_counts[2]==old[2]+(filtered ? target_kind ? 3 : 1 : 0));
        assert(sd_apc_notify_counts[3]==old[3]+(filtered && !target_kind ? 2-pending : 0));
        assert(observed_signals==signals+(filtered ? target_kind ? 0 : 2-pending : 3-pending)+routed);
        assert(observed_broadcasts==broadcasts+1);
        assert(fex_sync_router.broad_notices==legacy_before+routed);
        assert(w[0].notified==(pending || !filtered || !target_kind));
        assert(w[1].notified==!filtered);
        assert(w[2].notified==(!filtered || !target_kind));
        assert(!w[0].completed && !w[1].completed && w[2].completed && w[2].status==0x1234);
        assert(!w[0].status && !w[1].status && !requests[2].flags);
        sd_sync_waiters=NULL; horizon_server_sleepers=0;
        pes27_unregister(&fex_sync_router,&lw);
        pthread_mutex_unlock(&horizon_server_objects_mutex);
        for (int i=0;i<3;++i) assert(!pthread_cond_destroy(&w[i].condition));
        assert(!pthread_cond_destroy(&legacy));
        ++cases;
    }
    printf("PASS v18 %u notifier cases: flag, modes 0/1/2, legacy router/shared wake, duplicate target, nonalertable target, pending dedup, completed status, absent/null target\n",cases);
}

static void v18_rejected_cases(void)
{
    for (int enabled=0;enabled<=1;++enabled) {
        wine_nx_sd_apc_targeted_wake=enabled;
        uint64_t notices=sd_apc_notify_counts[0];
        assert(v18_queue(10,APC_USER,0,0,0x1234,sizeof(union apc_call)-1)==STATUS_INVALID_PARAMETER);
        assert(v18_queue(10,APC_USER+1,0,0,0x1234,sizeof(union apc_call))==STATUS_NOT_IMPLEMENTED);
        assert(v18_queue(10,APC_USER,0,1,0x1234,sizeof(union apc_call))==STATUS_NOT_IMPLEMENTED);
        assert(v18_queue(10,APC_USER,1,0,0x1234,sizeof(union apc_call))==STATUS_NOT_SUPPORTED);
        assert(v18_queue(10,APC_USER,0,0,0,sizeof(union apc_call))==STATUS_INVALID_PARAMETER);
        assert(v18_queue(99,APC_USER,0,0,0x1234,sizeof(union apc_call))==HORIZON_STATUS_INVALID_HANDLE);
        assert(v18_queue(1,APC_USER,0,0,0x1234,sizeof(union apc_call))==HORIZON_STATUS_OBJECT_TYPE_MISMATCH);
        threads[1].thread.terminated=1;
        assert(v18_queue(10,APC_USER,0,0,0x1234,sizeof(union apc_call))==STATUS_THREAD_IS_TERMINATING);
        threads[1].thread.terminated=0;
        assert(sd_apc_notify_counts[0]==notices && !threads[1].f1_apcs.head);
        threads[1].thread.suspend=1;
        assert(!v18_queue(10,APC_USER,0,0,0x1234,sizeof(union apc_call)));
        assert(sd_apc_notify_counts[0]==notices+1 && threads[1].f1_apcs.head);
        threads[1].thread.suspend=0;
        f1_apc_clear(&threads[1].f1_apcs);
    }
    puts("PASS v18 accepted enqueue only: malformed/unsupported/reserved/flags/null callback/invalid/wrong-type/terminated cause no notice; suspended target retains pending APC");
}

static void v18_wait_ready(unsigned queued, unsigned legacy)
{
    long long deadline=clock_ticks()+20000000;
    for (;;) {
        pthread_mutex_lock(&horizon_server_objects_mutex);
        unsigned seen=horizon_server_sleepers;
        if (wine_nx_fex_targeted_wake) {
            seen=0; for(struct pes27_waiter *w=fex_sync_router.head;w;w=w->next) ++seen;
        }
        int ready=sd_sync_counts[6]==queued && seen==legacy;
        pthread_mutex_unlock(&horizon_server_objects_mutex);
        if(ready) return;
        assert(clock_ticks()<deadline); usleep(100);
    }
}

static void v18_thread_cases(void)
{
    unsigned cases=0;
    for (int enabled=0;enabled<=1;++enabled)
    for (int routed=0;routed<=1;++routed)
    for (int mode=1;mode<=2;++mode)
    for (int alertable=0;alertable<=1;++alertable) {
        wine_nx_sd_apc_targeted_wake=enabled; wine_nx_fex_targeted_wake=routed; horizon_fast_sync_enabled=mode;
        clear_events();
        struct job target={.tid=2,.op=HORIZON_SELECT_WAIT,.h=1,.alertable=alertable};
        struct job unrelated={.tid=3,.op=HORIZON_SELECT_WAIT,.h=2};
        pthread_t a,b;
        assert(!pthread_create(&a,NULL,wait_job,&target));
        assert(!pthread_create(&b,NULL,wait_job,&unrelated));
        v18_wait_ready(mode==2 ? 2 : 0,mode==1 ? 2 : 0);
        assert(!v18_queue(10,APC_USER,0,0,0x1234,sizeof(union apc_call)));
        if (alertable) join(a,&target,STATUS_USER_APC);
        else {
            assert(!event(1,1,HORIZON_SET_EVENT)); join(a,&target,0);
            assert(threads[1].f1_apcs.head);
            assert(select_op(2,HORIZON_SELECT_WAIT,1,0,0,0,1,0)==STATUS_USER_APC);
        }
        assert(!threads[1].f1_apcs.head);
        assert(!event(1,2,HORIZON_SET_EVENT)); join(b,&unrelated,0);
        ++cases;
    }
    horizon_fast_sync_enabled=2; wine_nx_sd_apc_targeted_wake=1;
    for (int routed=0;routed<=1;++routed)
    for (int legacy=0;legacy<=1;++legacy)
    for (int op=0;op<3;++op) {
        wine_nx_fex_targeted_wake=routed; clear_events();
        struct job j={.tid=2,.op=op==0 ? HORIZON_SELECT_WAIT : op==1 ? HORIZON_SELECT_WAIT_ALL : HORIZON_SELECT_SIGNAL_AND_WAIT,
                      .h=1,.second=3,.two=op!=0,.alertable=1,.legacy=legacy};
        pthread_t t; assert(!pthread_create(&t,NULL,wait_job,&j));
        v18_wait_ready(!legacy,legacy);
        assert(!v18_queue(10,APC_USER,0,0,0x1234,sizeof(union apc_call)));
        join(t,&j,STATUS_USER_APC);
        assert(objects[3].signaled==(op==2)); /* signal-and-wait signals exactly once */
        ++cases;
    }
    wine_nx_fex_targeted_wake=0; clear_events();
    assert(!v18_queue(10,APC_USER,0,0,0x1234,sizeof(union apc_call)));
    assert(!event(1,1,HORIZON_SET_EVENT));
    assert(!select_op(2,HORIZON_SELECT_WAIT,1,0,0,0,1,0));
    assert(threads[1].f1_apcs.head); /* ready object wins before ordinary APC */
    assert(select_op(2,HORIZON_SELECT_WAIT,1,0,0,0,1,0)==STATUS_USER_APC);
    assert(!threads[1].f1_apcs.head);
    printf("PASS v18 %u threaded routing cases: flag/mode/router, alertable/nonalertable, legacy target, wait-all, signal-and-wait; object-before-APC ordering\n",cases);
}

static void *v18_apc_ping(void *arg)
{
    int loops=*(int *)arg;
    for(int i=0;i<loops;++i) {
        assert(select_op(2,HORIZON_SELECT_WAIT,1,0,0,-(clock_ticks()+20000000),1,0)==STATUS_USER_APC);
        assert(!event(2,3,HORIZON_SET_EVENT));
    }
    return NULL;
}

static void v18_cases(void)
{
    assert(wine_nx_sd_apc_targeted_wake==1);
    for(unsigned i=0;i<8;++i) threads[i].type=HORIZON_SERVER_OBJECT_THREAD;
    handles[10].object=threads+1;
    v18_helper_matrix();
    horizon_fast_sync_enabled=2; wine_nx_fex_targeted_wake=0;
    v18_rejected_cases();
    v18_thread_cases();
    for(int enabled=0;enabled<=1;++enabled)
    for(int routed=0;routed<=1;++routed) {
        wine_nx_sd_apc_targeted_wake=enabled; wine_nx_fex_targeted_wake=routed;
        clear_events(); int loops=1000;
        struct job other={.tid=3,.op=HORIZON_SELECT_WAIT,.h=2};
        pthread_t target,unrelated;
        assert(!pthread_create(&unrelated,NULL,wait_job,&other)); wait_queued(1,0);
        assert(!pthread_create(&target,NULL,v18_apc_ping,&loops));
        for(int i=0;i<loops;++i) {
            assert(!v18_queue(10,APC_USER,0,0,0x1234,sizeof(union apc_call)));
            assert(!wait_for(1,3,-(clock_ticks()+20000000)));
        }
        assert(!pthread_join(target,NULL));
        assert(!threads[1].f1_apcs.head);
        assert(!event(1,2,HORIZON_SET_EVENT)); join(unrelated,&other,0);
        assert(!sd_sync_waiters && !sd_sync_counts[6]);
    }
    puts("PASS v18 4000 concurrent APC/ack round trips with unrelated waiter, ON/OFF and shared/routed legacy: no lost wake or leaked queue");
    uint64_t out[5]; wine_nx_sd_apc_notify_snapshot(out);
    assert(out[0] && out[1] && out[2] && out[3] && out[4]);
    assert(!sd_sync_waiters && !sd_sync_counts[6]);
    handles[10].object=objects+10;
    wine_nx_fex_targeted_wake=0; horizon_fast_sync_enabled=2;
    f1_apc_delivered=0; /* isolate inherited direct-sync baseline assertions */
    puts("PASS v18 locked snapshot; inherited production queue/handler regression follows");
}
