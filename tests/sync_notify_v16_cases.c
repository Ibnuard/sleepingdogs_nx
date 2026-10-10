/* Production post-completion, set-timer and select/queue/router functions.
 * Host fixture supplies object lookup, clocks and pthreads, not Switch timing. */
static void v16_wait_registered(unsigned direct, unsigned legacy)
{
    long long deadline = clock_ticks() + 20000000;
    for (;;) {
        pthread_mutex_lock(&horizon_server_objects_mutex);
        unsigned n = horizon_server_sleepers;
        if (wine_nx_fex_targeted_wake) {
            n = 0;
            for (struct pes27_waiter *w = fex_sync_router.head; w; w = w->next) ++n;
        }
        int ready = sd_sync_counts[6] == direct && n == legacy;
        pthread_mutex_unlock(&horizon_server_objects_mutex);
        if (ready) break;
        assert(clock_ticks() < deadline);
        usleep(100);
    }
}

static void v16_cases(void)
{
    assert(wine_nx_sd_sync_notify_filter == 1);
    objects[7].type = HORIZON_SERVER_OBJECT_COMPLETION;
    objects[8].type = HORIZON_SERVER_OBJECT_COMPLETION_WAIT;
    objects[8].wait_port = objects + 7;
    for (int filter = 0; filter <= 1; ++filter) {
        for (int routed = 0; routed <= 1; ++routed) {
            wine_nx_sd_sync_notify_filter = filter;
            wine_nx_fex_targeted_wake = routed;
            clear_events();
            pthread_t qt, lt;
            struct job q = {.tid=2, .op=HORIZON_SELECT_WAIT, .h=1};
            struct job l = {.tid=3, .op=HORIZON_SELECT_WAIT, .h=8};
            objects[7].completion_closed = 0;
            objects[8].wait_has_msg = 0;
            assert(!pthread_create(&qt, NULL, wait_job, &q));
            assert(!pthread_create(&lt, NULL, wait_job, &l));
            v16_wait_registered(1, 1);
            pthread_mutex_lock(&horizon_server_objects_mutex);
            uint64_t broad = sd_sync_counts[2], candidates = sd_sync_legacy_counts[3];
            horizon_server_post_completion_locked(objects + 7, 0x1234, 0x5678, 0xc0000001u, 17);
            assert(sd_sync_counts[2] == broad + !filter);
            assert(sd_sync_legacy_counts[3] == candidates + filter);
            assert(sd_sync_waiters->notified == !filter && !sd_sync_waiters->completed);
            pthread_mutex_unlock(&horizon_server_objects_mutex);
            join(lt, &l, 0);
            assert(objects[8].wait_has_msg && !objects[7].completion.depth);
            assert(objects[8].wait_msg.ckey == 0x1234 && objects[8].wait_msg.cvalue == 0x5678);
            assert(objects[8].wait_msg.status == 0xc0000001u && objects[8].wait_msg.information == 17);
            assert(!event(1, 1, HORIZON_SET_EVENT));
            join(qt, &q, 0);

            /* Closing a port abandons the legacy completion waiter. The real
             * close handler's route is also checked in the source audit. */
            assert(!pthread_create(&qt, NULL, wait_job, &q));
            assert(!pthread_create(&lt, NULL, wait_job, &l));
            v16_wait_registered(1, 1);
            pthread_mutex_lock(&horizon_server_objects_mutex);
            broad = sd_sync_counts[2];
            objects[7].completion_closed = 1;
            sd_sync_signal_legacy_locked(SD_SYNC_COMPLETION_CLOSE);
            assert(sd_sync_counts[2] == broad + !filter);
            pthread_mutex_unlock(&horizon_server_objects_mutex);
            join(lt, &l, HORIZON_STATUS_ABANDONED_WAIT_0);
            assert(!event(1, 1, HORIZON_SET_EVENT));
            join(qt, &q, 0);
            objects[7].completion_closed = 0;

            /* A rearmed timer remains on the polling path and expires at its
             * real deadline, even when a direct event waiter is left asleep. */
            l.h = 6;
            objects[6].timer_when = clock_ticks() + 100000000;
            objects[6].signaled = 0;
            horizon_server_timers_armed = 1;
            assert(!pthread_create(&qt, NULL, wait_job, &q));
            assert(!pthread_create(&lt, NULL, wait_job, &l));
            v16_wait_registered(1, 1);
            pthread_mutex_lock(&horizon_server_objects_mutex);
            broad = sd_sync_counts[2];
            pthread_mutex_unlock(&horizon_server_objects_mutex);
            struct horizon_set_timer_request request = {.handle=6, .expire=-10000};
            struct horizon_server_connection c = {.tid=1, .thread=threads};
            assert(!horizon_server_handle_set_timer(&c, (const void *)&request));
            join(lt, &l, 0);
            assert(!objects[6].timer_when && !objects[6].signaled);
            pthread_mutex_lock(&horizon_server_objects_mutex);
            assert(sd_sync_counts[2] == broad + !filter);
            pthread_mutex_unlock(&horizon_server_objects_mutex);
            assert(!event(1, 1, HORIZON_SET_EVENT));
            join(qt, &q, 0);

            /* A mixed wait-all must stay entirely on the legacy route. */
            l.h=8; l.second=2; l.two=1; l.op=HORIZON_SELECT_WAIT_ALL;
            assert(!pthread_create(&qt, NULL, wait_job, &q));
            assert(!pthread_create(&lt, NULL, wait_job, &l));
            v16_wait_registered(1, 1);
            pthread_mutex_lock(&horizon_server_objects_mutex);
            horizon_server_post_completion_locked(objects + 7, 3, 4, 0, 5);
            assert(sd_sync_counts[6] == 1);
            pthread_mutex_unlock(&horizon_server_objects_mutex);
            assert(!event(1, 2, HORIZON_SET_EVENT));
            join(lt, &l, 0);
            assert(!objects[7].completion.depth && !objects[2].signaled);
            assert(!event(1, 1, HORIZON_SET_EVENT));
            join(qt, &q, 0);
        }
    }
    puts("PASS v16 ON/OFF x shared/routed legacy waits: IOCP data/status, port close, timer rearm/deadline, mixed wait-all; unrelated direct waiter excluded only when ON");

    /* Modes without direct queues preserve the original notification path. */
    wine_nx_sd_sync_notify_filter=1;
    for (int mode=0; mode<=1; ++mode) {
        horizon_fast_sync_enabled=mode;
        pthread_mutex_lock(&horizon_server_objects_mutex);
        uint64_t notices=fex_sync_router.broad_notices, skipped=sd_sync_legacy_counts[3];
        sd_sync_signal_legacy_locked(SD_SYNC_TIMER_REARM);
        assert(fex_sync_router.broad_notices == notices+1);
        assert(sd_sync_legacy_counts[3] == skipped);
        pthread_mutex_unlock(&horizon_server_objects_mutex);
    }
    horizon_fast_sync_enabled=2;
    wine_nx_fex_targeted_wake=0;
    objects[7].type=objects[8].type=HORIZON_SERVER_OBJECT_EVENT;
    uint64_t out[5];
    wine_nx_sd_sync_notify_snapshot(out);
    assert(out[0] == 1 && out[1] && out[2] && out[3] && out[4]);
    puts("PASS v16 modes 0/1 fallback and locked counter snapshot; original APC/termination tests run next");
}
