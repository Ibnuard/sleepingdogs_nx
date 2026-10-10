/* LGPL-2.1-or-later. Caller holds mapping_mutex. Only completely returned
 * arenas are disposable; mapped/live/partial arenas never move or change.
 */
#ifndef FEXTENDO_POOL_PRESSURE_H
#define FEXTENDO_POOL_PRESSURE_H
static size_t horizon_pages_trim(struct horizon_page_pool *pool){
    size_t released=0;
    for(unsigned i=0;i<HORIZON_POOL_ARENAS;i++){
        struct horizon_page_arena *a=&pool->arenas[i];
        if(!a->memory||a->free_pages!=HORIZON_POOL_PAGES)continue;
        unsigned j=0;while(j<HORIZON_POOL_PAGES&&!a->used[j])j++;
        if(j!=HORIZON_POOL_PAGES)continue;
        void *p=a->memory;memset(a,0,sizeof(*a));free(p);
        released+=(size_t)HORIZON_POOL_PAGE*HORIZON_POOL_PAGES;
    }
    return released;
}
#endif
