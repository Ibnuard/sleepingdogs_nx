/* SPDX-License-Identifier: MIT
 * Last-resort FEX CPU data storage from fragmented heap pages. Scratch, lookup
 * and private CRT allocations share this path regardless of request size.
 * Only the contiguous RW alias is published; sources stay owned until every
 * alias is unmapped. No executable/GPU memory or per-access copying here. */
#ifndef PES13_HORIZON_SCRATCH_PAGES_H
#define PES13_HORIZON_SCRATCH_PAGES_H
#define FX_SP_SLOTS 128u
#define FX_SP_MIN PAGE_BYTES
#define FX_SP_CHUNK (1024u*1024u)
#define FX_SP_BUDGET (128u*1024u*1024u)
#define FX_SP_MAX FX_SP_BUDGET
#define FX_SP_PIECES (FX_SP_BUDGET/PAGE_BYTES)
#define FX_SP_NONE UINT32_MAX
enum {FX_SP_FREE,FX_SP_BUILDING,FX_SP_LIVE,FX_SP_RELEASING,FX_SP_QUARANTINE,FX_SP_DRAINING};
enum {FX_SP_OK,FX_SP_INVALID_SIZE,FX_SP_LIMIT_BYTES,FX_SP_LIMIT_OWNERS,
      FX_SP_SOURCE_ALLOC,FX_SP_DESCRIPTOR,FX_SP_VIRTUAL_RANGE,FX_SP_RESERVATION,FX_SP_MAP,FX_SP_PERMISSION};
struct fx_sp_failure {unsigned stage;Result result;};
struct fx_sp_piece {void *source;size_t size,offset;unsigned mapped,next;};
struct fx_sp_slot {
    void *alias;size_t size;VirtmemReservation *reservation;
    void *cpu_address;
    size_t cpu_size;
    unsigned borrowed,process;
    unsigned state,count,first,last;
};
static struct fx_sp_slot fx_sp_slots[FX_SP_SLOTS];
/* Shared descriptors cover the entire byte budget even at 4-KiB granularity.
 * Metadata is bounded/static so recovery doesn't need another heap malloc.
 * A buffer consumes only as many descriptors as its actual fragments need. */
static struct fx_sp_piece fx_sp_pieces[FX_SP_PIECES];
static unsigned fx_sp_piece_head,fx_sp_piece_ready;
#ifdef __SWITCH__
static host_mutex fx_sp_lock;
#else
static host_mutex fx_sp_lock=PTHREAD_MUTEX_INITIALIZER;
#endif
/* attempts, recovered, failed, held bytes, peak bytes, held slots, pieces,
 * returned, map failures, unmap failures, quarantined, invalid release,
 * last kernel Result, last requested size, budget refusals. */
static uint64_t fx_sp_stats[15];
static size_t fx_sp_held;
/* Ordinary native-heap frees should not scan fallback ownership or take its
 * lock. Bounds only expand; successful allocation publishes them before the
 * caller can receive an alias. Interior/quarantined aliases still get checked. */
static uintptr_t fx_sp_alias_low=UINTPTR_MAX,fx_sp_alias_high;
static void fx_sp_publish_range(uintptr_t lo,uintptr_t hi){
    uintptr_t old=__atomic_load_n(&fx_sp_alias_low,__ATOMIC_RELAXED);
    while(lo<old&&!__atomic_compare_exchange_n(&fx_sp_alias_low,&old,lo,0,__ATOMIC_RELAXED,__ATOMIC_RELAXED)){}
    old=__atomic_load_n(&fx_sp_alias_high,__ATOMIC_RELAXED);
    while(hi>old&&!__atomic_compare_exchange_n(&fx_sp_alias_high,&old,hi,0,__ATOMIC_RELAXED,__ATOMIC_RELAXED)){}
}
static unsigned fx_sp_piece_take(void){
    HOST_LOCK(&fx_sp_lock);
    if(!fx_sp_piece_ready){
        for(unsigned i=0;i<FX_SP_PIECES;i++)fx_sp_pieces[i].next=i+1;
        fx_sp_pieces[FX_SP_PIECES-1].next=FX_SP_NONE;
        fx_sp_piece_ready=1;
    }
    unsigned i=fx_sp_piece_head;
    if(i!=FX_SP_NONE)fx_sp_piece_head=fx_sp_pieces[i].next;
    HOST_UNLOCK(&fx_sp_lock);
    return i;
}
static void fx_sp_add(unsigned n,uint64_t v){__atomic_fetch_add(&fx_sp_stats[n],v,__ATOMIC_RELAXED);}
static void fx_sp_peak(uint64_t n){
    uint64_t old=__atomic_load_n(&fx_sp_stats[4],__ATOMIC_RELAXED);
    while(old<n&&!__atomic_compare_exchange_n(&fx_sp_stats[4],&old,n,0,__ATOMIC_RELAXED,__ATOMIC_RELAXED)){}
}
static void fx_sp_quarantine(struct fx_sp_slot *s){
    fx_sp_add(10,1);
    fx_sp_publish_range((uintptr_t)s->alias,(uintptr_t)s->alias+s->size);
    HOST_LOCK(&fx_sp_lock);s->state=FX_SP_QUARANTINE;HOST_UNLOCK(&fx_sp_lock);
}
/* Preserve the reservation and every source allocation if even one unmap
 * fails. A caller can never receive a partially mapped or recycled buffer. */
static int fx_sp_dispose(struct fx_sp_slot *s){
    int failed=0;
#ifdef FX_SHARED_CPU_RECOVERY
    if(s->borrowed){
        HOST_LOCK(&fx_sp_lock);s->state=FX_SP_DRAINING;s->cpu_address=NULL;HOST_UNLOCK(&fx_sp_lock);
        fx_scratch_reserve_return(s->alias);
        HOST_LOCK(&fx_sp_lock);
        fx_sp_held-=s->size;fx_sp_add(3,-s->size);fx_sp_add(5,-1);
        memset(s,0,sizeof(*s));HOST_UNLOCK(&fx_sp_lock);
        return 1;
    }
#endif
    for(unsigned i=s->first;i!=FX_SP_NONE;i=fx_sp_pieces[i].next){
        struct fx_sp_piece *p=&fx_sp_pieces[i];
        if(!p->mapped)continue;
        Result rc;
#if defined(__SWITCH__) || defined(FX_SP_CODE_ALIAS)
        if(s->process)rc=svcUnmapProcessCodeMemory(s->process,(uintptr_t)s->alias+p->offset,(uintptr_t)p->source,p->size);
        else
#endif
            rc=svcUnmapMemory((char *)s->alias+p->offset,p->source,p->size);
        if(R_FAILED(rc)){
            __atomic_store_n(&fx_sp_stats[12],rc,__ATOMIC_RELAXED);fx_sp_add(9,1);failed=1;
        }else p->mapped=0;
    }
    if(failed){fx_sp_quarantine(s);return 0;}
    /* Retire address ownership BEFORE the virtual reservation is removed.
     * Otherwise another thread can receive this same VA and have its free
     * swallowed by the old RELEASING record while we dispose source pages. */
    HOST_LOCK(&fx_sp_lock);s->state=FX_SP_DRAINING;s->cpu_address=NULL;HOST_UNLOCK(&fx_sp_lock);
    if(s->reservation){virtmemLock();virtmemRemoveReservation(s->reservation);virtmemUnlock();}
    for(unsigned i=s->first;i!=FX_SP_NONE;i=fx_sp_pieces[i].next)free(fx_sp_pieces[i].source);
    fx_sp_add(6,-(uint64_t)s->count);
    HOST_LOCK(&fx_sp_lock);
    if(s->count){fx_sp_pieces[s->last].next=fx_sp_piece_head;fx_sp_piece_head=s->first;}
    fx_sp_held-=s->size;fx_sp_add(3,-(uint64_t)s->size);fx_sp_add(5,-UINT64_C(1));
    s->alias=NULL;s->reservation=NULL;s->cpu_address=NULL;s->count=0;s->size=0;s->state=FX_SP_FREE;
    HOST_UNLOCK(&fx_sp_lock);
    return 1;
}
static void *fx_scratch_pages_take_report(size_t size,struct fx_sp_failure *report){
    struct fx_sp_failure failure={FX_SP_INVALID_SIZE,0};
    int vm_locked=0;
    if(report)*report=failure;
    if(!size||size>FX_SP_MAX||size%PAGE_BYTES)return NULL;
    fx_sp_add(0,1);__atomic_store_n(&fx_sp_stats[13],size,__ATOMIC_RELAXED);
    struct fx_sp_slot *s=NULL;
    HOST_LOCK(&fx_sp_lock);
    failure.stage=FX_SP_LIMIT_BYTES;
    if(size<=FX_SP_BUDGET-fx_sp_held){
        failure.stage=FX_SP_LIMIT_OWNERS;
        for(unsigned i=0;i<FX_SP_SLOTS;i++)if(fx_sp_slots[i].state==FX_SP_FREE){
            s=&fx_sp_slots[i];s->state=FX_SP_BUILDING;s->size=size;
            s->alias=NULL;s->reservation=NULL;s->cpu_address=NULL;s->cpu_size=0;s->borrowed=0;s->process=0;s->count=0;
            s->first=s->last=FX_SP_NONE;
            fx_sp_held+=size;fx_sp_add(3,size);fx_sp_add(5,1);fx_sp_peak(fx_sp_held);break;
        }
    }
    HOST_UNLOCK(&fx_sp_lock);
    if(!s){fx_sp_add(14,1);fx_sp_add(2,1);if(report)*report=failure;return NULL;}
    size_t left=size,ceiling=FX_SP_CHUNK;
    while(left){
        size_t n=left<ceiling?left:ceiling;
        void *p;
        while(!(p=aligned_alloc(PAGE_BYTES,n))){
            if(n<=FX_SP_MIN)break;
            n=(n/2)&~(size_t)(PAGE_BYTES-1);
            if(n<FX_SP_MIN)n=FX_SP_MIN;
            ceiling=n;
        }
        if(!p){failure.stage=FX_SP_SOURCE_ALLOC;goto failed;}
        unsigned i=fx_sp_piece_take();
        if(i==FX_SP_NONE){free(p);failure.stage=FX_SP_DESCRIPTOR;goto failed;}
        fx_sp_pieces[i]=(struct fx_sp_piece){p,n,size-left,0,FX_SP_NONE};
        if(s->count)fx_sp_pieces[s->last].next=i;
        else s->first=i;
        s->last=i;s->count++;
        fx_sp_add(6,1);left-=n;
    }
    if(left)goto failed;
#if defined(__SWITCH__) || defined(FX_SP_CODE_ALIAS)
    /* These are CPU DATA aliases. MapMemory restricts them to the small stack
     * window (under 1 GiB in 32-bit no-alias mode), even when ASLR has room.
     * Use Wine's existing process-code mapping protocol, with RW permission
     * only. This needs no new kernel handles and never publishes RX/RWX data.
     * Keep the stack protocol for a host without the required capabilities. */
    if(envIsSyscallHinted(0x73)&&envIsSyscallHinted(0x77)&&envIsSyscallHinted(0x78))
        s->process=envGetOwnProcessHandle();
#endif
    virtmemLock();
    vm_locked=1;
#if defined(__SWITCH__) || defined(FX_SP_CODE_ALIAS)
    s->alias=s->process?virtmemFindCodeMemory(size,PAGE_BYTES):virtmemFindStack(size,PAGE_BYTES);
#else
    s->alias=virtmemFindStack(size,PAGE_BYTES);
#endif
    if(s->alias)s->reservation=virtmemAddReservation(s->alias,size);
    /* Wine's fixed-address path checks kernel occupancy under this same lock.
     * Keep it until every piece is mapped: a software reservation alone is
     * invisible to that check during the find-to-map window. No heap allocation
     * or fx_sp_lock acquisition occurs while this mapping lock is held. */
    if(!s->alias||!s->reservation){
        failure.stage=s->alias?FX_SP_RESERVATION:FX_SP_VIRTUAL_RANGE;goto failed;
    }
    for(unsigned i=s->first;i!=FX_SP_NONE;i=fx_sp_pieces[i].next){
        struct fx_sp_piece *p=&fx_sp_pieces[i];
        Result rc;
#if defined(__SWITCH__) || defined(FX_SP_CODE_ALIAS)
        if(s->process)rc=svcMapProcessCodeMemory(s->process,(uintptr_t)s->alias+p->offset,(uintptr_t)p->source,p->size);
        else
#endif
            rc=svcMapMemory((char *)s->alias+p->offset,p->source,p->size);
        if(R_FAILED(rc)){
            failure.stage=FX_SP_MAP;failure.result=rc;
            fx_sp_add(8,1);__atomic_store_n(&fx_sp_stats[12],rc,__ATOMIC_RELAXED);goto failed;
        }
        p->mapped=1;
#if defined(__SWITCH__) || defined(FX_SP_CODE_ALIAS)
        if(s->process){
            rc=svcSetProcessMemoryPermission(s->process,(uintptr_t)s->alias+p->offset,p->size,Perm_Rw);
            if(R_FAILED(rc)){
                /* The current piece IS mapped even if setting RW failed. */
                failure.stage=FX_SP_PERMISSION;failure.result=rc;
                fx_sp_add(8,1);__atomic_store_n(&fx_sp_stats[12],rc,__ATOMIC_RELAXED);goto failed;
            }
        }
#endif
    }
    virtmemUnlock();vm_locked=0;
    fx_sp_publish_range((uintptr_t)s->alias,(uintptr_t)s->alias+s->size);
    HOST_LOCK(&fx_sp_lock);s->state=FX_SP_LIVE;HOST_UNLOCK(&fx_sp_lock);
    fx_sp_add(1,1);if(report)*report=(struct fx_sp_failure){FX_SP_OK,0};return s->alias;
failed:
    if(vm_locked)virtmemUnlock();
    fx_sp_add(2,1);fx_sp_dispose(s);if(report)*report=failure;return NULL;
}
static __attribute__((noinline,used)) void *fx_scratch_pages_take(size_t size){
    return fx_scratch_pages_take_report(size,NULL);
}
/* Return 1 for owned/interior/quarantined aliases so libc never sees them. */
static __attribute__((noinline,used)) int fx_scratch_pages_release(void *address){
    struct fx_sp_slot *s=NULL;uintptr_t at=(uintptr_t)address;int retired=0;
    int maybe=at>=__atomic_load_n(&fx_sp_alias_low,__ATOMIC_RELAXED)&&
              at<__atomic_load_n(&fx_sp_alias_high,__ATOMIC_RELAXED);
#ifdef FX_SHARED_CPU_RECOVERY
    maybe|=fx_scratch_reserve_contains(address);
#endif
    if(!maybe)return 0;
    HOST_LOCK(&fx_sp_lock);
    for(unsigned i=0;i<FX_SP_SLOTS;i++){
        struct fx_sp_slot *p=&fx_sp_slots[i];
        if(p->state==FX_SP_FREE||p->state==FX_SP_BUILDING||!p->alias||
           at<(uintptr_t)p->alias||at-(uintptr_t)p->alias>=p->size)continue;
        if(p->state==FX_SP_DRAINING){retired=1;continue;}
        if(at!=(uintptr_t)p->alias||p->state!=FX_SP_LIVE){
            fx_sp_add(11,1);HOST_UNLOCK(&fx_sp_lock);return 1;
        }
        s=p;s->state=FX_SP_RELEASING;
        /* A reserve address may be reissued as soon as it is returned. */
        if(s->borrowed)s->cpu_address=NULL;
        break;
    }
    HOST_UNLOCK(&fx_sp_lock);
    if(!s)return retired;
    if(fx_sp_dispose(s))fx_sp_add(7,1);
    return 1;
}
void pes13_fex_scratch_pages_snapshot(uint64_t out[15]){
    for(unsigned i=0;i<15;i++)out[i]=__atomic_load_n(&fx_sp_stats[i],__ATOMIC_RELAXED);
}
/* Native Rust's shader compiler owns ordinary CPU data, not driver/GPU
 * allocations. It can use the same bounded pages only after its normal
 * allocator fails. Keep ownership in static metadata, never before a foreign
 * pointer: native malloc pointers have no custom header. */
void *pes13_cpu_pages_allocate(size_t size,size_t alignment){
    if(!size||!alignment||(alignment&(alignment-1))||alignment>FX_SP_BUDGET)return NULL;
    size_t padding=alignment>PAGE_BYTES?alignment-1:0;
    if(size>SIZE_MAX-padding-(PAGE_BYTES-1))return NULL;
    size_t rounded=(size+padding+PAGE_BYTES-1)&~(size_t)(PAGE_BYTES-1);
#ifdef FX_SHARED_CPU_RECOVERY
    size_t trimmed=fx_heap_pressure_trim();
    if(trimmed){
        size_t a=alignment>PAGE_BYTES?alignment:PAGE_BYTES;
        if(size<=SIZE_MAX-(a-1)){
            void *p=aligned_alloc(a,(size+a-1)&~(a-1));
            if(p){fx_heap_pressure_report("native-cpu",size,alignment,0,0,trimmed,1);return p;}
        }
    }
#endif
    struct fx_sp_failure failure={FX_SP_INVALID_SIZE,0};
    void *raw=fx_scratch_pages_take_report(rounded,&failure);
#ifdef FX_SHARED_CPU_RECOVERY
    /* Native Mesa C and Rust data share the same failure policy as FEX:
     * fragmented pages first, then genuinely idle pages of the old reserve.
     * Use the same bounded owner table for correct realloc/free routing. */
    if(!raw){
        raw=fx_scratch_reserve_try(rounded,1);
        if(raw){
            struct fx_sp_slot *slot=NULL;
            HOST_LOCK(&fx_sp_lock);
            if(rounded<=FX_SP_BUDGET-fx_sp_held)
                for(unsigned i=0;i<FX_SP_SLOTS;i++)if(fx_sp_slots[i].state==FX_SP_FREE){slot=&fx_sp_slots[i];break;}
            if(slot){
                *slot=(struct fx_sp_slot){.alias=raw,.size=rounded,.state=FX_SP_LIVE,.first=FX_SP_NONE,.last=FX_SP_NONE,.borrowed=1};
                fx_sp_held+=rounded;fx_sp_add(3,rounded);fx_sp_add(5,1);fx_sp_peak(fx_sp_held);
            }
            HOST_UNLOCK(&fx_sp_lock);
            if(!slot){fx_scratch_reserve_return(raw);raw=NULL;}
        }
    }
    fx_heap_pressure_report("native-cpu",size,alignment,failure.stage,failure.result,trimmed,raw!=NULL);
#endif
    if(!raw)return NULL;
    void *user=(void *)(((uintptr_t)raw+alignment-1)&~(uintptr_t)(alignment-1));
    HOST_LOCK(&fx_sp_lock);
    for(unsigned i=0;i<FX_SP_SLOTS;i++)if(fx_sp_slots[i].alias==raw&&fx_sp_slots[i].state==FX_SP_LIVE){
        fx_sp_slots[i].cpu_address=user;fx_sp_slots[i].cpu_size=size;break;
    }
    HOST_UNLOCK(&fx_sp_lock);
    return user;
}
/* Shared read/release lookup. An ordinary pointer outside the alias range
 * takes no lock; the native fast path retains its original allocator. */
static void *fx_cpu_pages_owner(void *address,size_t *size){
    uintptr_t at=(uintptr_t)address;void *raw=NULL;
    int maybe=at>=__atomic_load_n(&fx_sp_alias_low,__ATOMIC_RELAXED)&&
              at<__atomic_load_n(&fx_sp_alias_high,__ATOMIC_RELAXED);
#ifdef FX_SHARED_CPU_RECOVERY
    maybe|=fx_scratch_reserve_contains(address);
#endif
    if(!maybe)return NULL;
    HOST_LOCK(&fx_sp_lock);
    for(unsigned i=0;i<FX_SP_SLOTS;i++){
        struct fx_sp_slot *s=&fx_sp_slots[i];
        if(s->cpu_address==address&&s->state!=FX_SP_FREE){raw=s->alias;if(size)*size=s->cpu_size;break;}
    }
    HOST_UNLOCK(&fx_sp_lock);
    return raw;
}
int pes13_cpu_pages_owned(void *address){return fx_cpu_pages_owner(address,NULL)!=NULL;}
size_t pes13_cpu_pages_size(void *address){size_t size=0;fx_cpu_pages_owner(address,&size);return size;}
int pes13_cpu_pages_release(void *address){
    void *raw=fx_cpu_pages_owner(address,NULL);
    return raw?fx_scratch_pages_release(raw):0;
}
#endif
