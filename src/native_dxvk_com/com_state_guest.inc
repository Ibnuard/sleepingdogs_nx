/* SPDX-License-Identifier: MIT
 * One owner per context. A second rendering thread permanently falls back to
 * synchronous transport. No guest lock is held while entering native DXVK,
 * avoiding a lock inversion with ID3D10Multithread::Enter.
 */
static struct sd_state_cache *proxy_state_owner(void *object) {
    struct sd_state_cache *cache=((struct proxy*)object)->state_cache;
    if(!cache||__atomic_load_n(&cache->disabled,__ATOMIC_ACQUIRE))return NULL;
    /* Windows x86 TEB ClientId.UniqueThread; no Wine/native call for a TID. */
    uint32_t tid=__readfsdword(0x24),owner=__atomic_load_n(&cache->owner,__ATOMIC_ACQUIRE);
    if(!owner) {
        uint32_t expected=0;
        if(__atomic_compare_exchange_n(&cache->owner,&expected,tid,0,__ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE))owner=tid;
        else owner=expected;
    }
    /* Emit a locked x86 exchange before any foreign native mutation. FEX
     * Fastest may relax ordinary stores; a release-only MOV is insufficient. */
    if(owner!=tid){__atomic_store_n(&cache->disabled,1,__ATOMIC_SEQ_CST);return NULL;}
    return cache;
}
static void proxy_state_invalidate(void *object) {
    struct sd_state_cache *cache=proxy_state_owner(object);
    if(cache){cache->valid=0;++cache->epoch;}
}
static LONG proxy_state_call(void *object,struct sd_com_packet *packet) {
    struct sd_state_cache *cache=proxy_state_owner(object);
    if(!cache)return proxy_call(packet);
    if(cache->busy){cache->valid=0;++cache->epoch;return proxy_call(packet);}
    int slot=sd_state_slot(packet->method);if(slot<0)return proxy_call(packet);
    uint32_t bit=1u<<slot;
    struct sd_state_key key;
    __atomic_store_n(&cache->attempts[slot],__atomic_load_n(&cache->attempts[slot],__ATOMIC_RELAXED)+1,__ATOMIC_RELAXED);
    int cacheable=sd_state_make_key(packet,&key)>=0;
    if(cacheable&&(cache->valid&bit)&&sd_state_equal(&key,&cache->keys[slot])) {
        __atomic_store_n(&cache->hits[slot],__atomic_load_n(&cache->hits[slot],__ATOMIC_RELAXED)+1,__ATOMIC_RELAXED);
        return 0;
    }
    cache->valid&=~bit;cache->busy=1;uint32_t epoch=cache->epoch;
    LONG result=proxy_call(packet);cache->busy=0;
    if(cacheable&&result>=0&&!packet->fault&&cache->epoch==epoch&&!__atomic_load_n(&cache->disabled,__ATOMIC_ACQUIRE)) {
        cache->keys[slot].count=key.count;
        memcpy(cache->keys[slot].words,key.words,key.count*4);cache->valid|=bit;
    }
    return result;
}
static void proxy_state_report(uint32_t presents) {
    struct sd_com_packet p={SD_COM_ABI,0,0,SD_COM_STATE_REPORT};
    p.args[0]=1;p.args[1]=presents;
    EnterCriticalSection(&proxy_lock);
    for(struct proxy *v=proxies;v;v=v->next)if(v->state_cache) {
        struct sd_state_cache *cache=v->state_cache;++p.args[5];
        p.args[4]+=!!__atomic_load_n(&cache->disabled,__ATOMIC_ACQUIRE);
        for(unsigned i=0;i<SD_STATE_SLOTS;++i) {
            uint32_t hits=__atomic_load_n(&cache->hits[i],__ATOMIC_RELAXED);
            p.args[2]+=__atomic_load_n(&cache->attempts[i],__ATOMIC_RELAXED);p.args[3]+=hits;
            p.args[i<6?6:i<12?7:i<18?8:9]+=hits;
        }
    }
    LeaveCriticalSection(&proxy_lock);
    proxy_call(&p); /* Reporting must never fail a game call. */
}
