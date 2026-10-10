"""PES13 page storage, copied for the isolated F1 Wine source overlay.

Only the header source directory differs from fextendo_page_store_patches.py.
"""
import shutil

def replace(data, old, new):
    assert data.count(old) == 1, (old, data.count(old))
    return data.replace(old, new)

def apply(source, project):
    directory = source/'dlls/ntdll/unix'
    changed = set()
    for name in ('horizon_page_store.h', 'horizon_store_backing.h','horizon_pool_pressure.h'):
        shutil.copy2(project/name, directory/name)
        changed.add('dlls/ntdll/unix/'+name)
    p = directory/'horizon.c'; s = p.read_text()
    s=replace(s,'static unsigned long long backing_direct_allocs;', '''static unsigned long long backing_direct_allocs;
#include "horizon_pool_pressure.h"
size_t wine_nx_release_idle_backing_pages(void)
{
    /* Allocation can occur below Wine's mapping lock. Never wait or recurse
     * on that lock during recovery. Another thread may retry later. */
    if (pthread_mutex_trylock(&mapping_mutex)) return 0;
    size_t released=horizon_pages_trim(&backing_pages);
    pthread_mutex_unlock(&mapping_mutex);
    return released;
}''')
    s = replace(s, 'struct horizon_backing\n{\n    void *heap_addr;',
        '#include "horizon_page_store.h"\n\nstruct horizon_backing\n{\n    struct horizon_page_store pages;')
    s = replace(s, 'static void free_backing( struct horizon_backing *backing, BOOL write_back )',
        '#include "horizon_store_backing.h"\n\nstatic void free_backing( struct horizon_backing *backing, BOOL write_back )')
    s = replace(s, '    if (write_back && backing->write_back && backing->fd != -1)\n        write_fd_at( backing->fd, backing->heap_addr, backing->size, backing->file_offset );',
        '    if (backing->pages.poisoned) return; /* Never recycle pages still owned by the kernel. */\n'
        '    if (write_back && backing->write_back && backing->fd != -1)\n'
        '        horizon_backing_io( backing, backing->fd, backing->file_offset, 1 );')
    s = replace(s, '    if (!horizon_pages_free( &backing_pages, backing->heap_addr, backing->size ))\n        free( backing->heap_addr );',
        '    horizon_store_free( &backing->pages, horizon_backing_pages_free );')
    s = replace(s, 'static int map_code_memory_range( void *addr, void *source, size_t size, int prot, int map_errno )',
        'static int map_code_memory_range_ex( void *addr, void *source, size_t size, int prot, int map_errno, unsigned *retained )')
    s = replace(s, '        svcUnmapProcessCodeMemory( envGetOwnProcessHandle(), (u64)addr, (u64)source, size );\n        return -1;',
        '        if (R_FAILED(svcUnmapProcessCodeMemory( envGetOwnProcessHandle(), (u64)addr, (u64)source, size )) && retained)\n'
        '        { *retained = 1; horizon_store_add(HS_ROLLBACK_FAILED, 1); }\n        return -1;')
    s = replace(s, 'static int unmap_code_memory_range( void *addr, void *source, size_t size )\n{',
        'static int map_code_memory_range( void *addr, void *source, size_t size, int prot, int map_errno )\n'
        '{\n    return map_code_memory_range_ex(addr, source, size, prot, map_errno, NULL);\n}\n\n'
        'static int unmap_code_memory_range( void *addr, void *source, size_t size )\n{')
    start = s.index('    backing->heap_addr = horizon_pages_alloc( &backing_pages, size );')
    end = s.index('\n\n', s.index('    memset( backing->heap_addr, 0, size );', start))
    s = s[:start]+'''    if (horizon_store_alloc( &backing->pages, size, horizon_backing_pages_alloc,
                              horizon_backing_pages_free ))
    {
        horizon_object_free( &backing_pool, backing );
        return NULL;
    }'''+s[end:]
    s = replace(s, 'read_fd_at( fd, backing->heap_addr, size, offset )', 'horizon_backing_io( backing, fd, offset, 0 )')
    s = replace(s, 'map_code_memory_range( addr, backing->heap_addr, size, prot, map_errno )',
        'horizon_backing_map( backing, addr, 0, size, prot, map_errno )')
    s = replace(s, 'addr, backing->heap_addr, (unsigned long)size, prot, errno );',
        'addr, backing->pages.data, (unsigned long)size, prot, errno );\n        if (backing->pages.poisoned) return -1;')
    s = replace(s, 'unmap_code_memory_range( addr, backing->heap_addr, size )',
        'horizon_backing_unmap( backing, addr, 0, size, get_effective_horizon_prot(prot) )')
    s = replace(s, '    void *source = (char *)mapping->backing->heap_addr + mapping->source_offset + offset;\n', '')
    s = replace(s, 'unmap_code_memory_range( start, source, size )',
        'horizon_backing_unmap( mapping->backing, start, mapping->source_offset + offset, size, mapping->prot )')
    s = replace(s, '    void *source = (char *)mapping->backing->heap_addr + mapping->source_offset;\n', '')
    s = replace(s, 'unmap_code_memory_range( mapping->addr, source, mapping->size )',
        'horizon_backing_unmap( mapping->backing, mapping->addr, mapping->source_offset, mapping->size, old_prot )')
    for prot in ('prot', 'old_prot'):
        s = replace(s, f'map_code_memory_range( mapping->addr, source, mapping->size, {prot}, EINVAL )',
            f'horizon_backing_map( mapping->backing, mapping->addr, mapping->source_offset, mapping->size, {prot}, EINVAL )')
    s = replace(s, 'set_code_memory_perm( mapping->addr, source, mapping->size, prot, FALSE )',
        'horizon_backing_protect( mapping, prot )')
    assert 'heap_addr' not in s
    p.write_text(s); changed.add('dlls/ntdll/unix/horizon.c')

    p = directory/'horizon_memfile.h'; s = p.read_text()
    s = replace(s, '#include <errno.h>', '#include "horizon_page_store.h"\n#include <errno.h>')
    s = replace(s, '    unsigned char *data;       /* the kernel locks the pages that are anchored */',
        '    struct horizon_page_store pages; /* Anchors never cross a storage piece. */')
    s = replace(s, '/* Zeroed whole pages, like a new temporary file grown to the section\'s size;',
        'static inline void *horizon_memfile_pages_alloc(size_t size) { return HORIZON_MEMFILE_ALLOC_PAGES(size); }\n'
        'static inline void horizon_memfile_pages_free(void *ptr, size_t size) { (void)size; HORIZON_MEMFILE_FREE_PAGES(ptr, size); }\n\n'
        '/* Zeroed whole pages, like a new temporary file grown to the section\'s size;')
    s = replace(s, '    if (!(file->data = HORIZON_MEMFILE_ALLOC_PAGES( size )) ||',
        '    if (horizon_store_alloc( &file->pages, size, horizon_memfile_pages_alloc, horizon_memfile_pages_free ) ||')
    s = replace(s, '        if (file->data) HORIZON_MEMFILE_FREE_PAGES( file->data, size );',
        '        horizon_store_free( &file->pages, horizon_memfile_pages_free );')
    s = replace(s, '    memset( file->data, 0, size );\n', '')
    s = replace(s, '    if (!file->anchors) HORIZON_MEMFILE_FREE_PAGES( file->data, file->size );',
        '    if (!file->anchors) horizon_store_free( &file->pages, horizon_memfile_pages_free );')
    s = replace(s, '    while ((anchor = *next))\n    {\n        if (anchor->users ||',
        '    while ((anchor = *next))\n    {\n        size_t available;\n'
        '        void *source = horizon_store_at(&file->pages, anchor->first * page_size, &available);\n'
        '        if (anchor->users ||')
    s = replace(s, 'file->data + anchor->first * page_size,', 'source,')
    s = replace(s, '        size_t stop;\n\n        while (*next',
        '        size_t stop, available;\n        void *source;\n\n        while (*next')
    s = replace(s, '        stop = *next && (*next)->first < end ? (*next)->first : end;',
        '        stop = *next && (*next)->first < end ? (*next)->first : end;\n'
        '        source = horizon_store_at(&file->pages, page * page_size, &available);\n'
        '        if (stop - page > available / page_size) stop = page + available / page_size;')
    s = replace(s, 'file->data + page * page_size,', 'source,')
    s = replace(s, '            ptr = file->data + offset;',
        '            size_t available;\n            ptr = horizon_store_at(&file->pages, offset, &available);\n'
        '            if (stop - offset > available) stop = offset + available;')
    assert 'file->data' not in s
    p.write_text(s); changed.add('dlls/ntdll/unix/horizon_memfile.h')
    p=directory/'horizon_pool.h';s=p.read_text()
    start=s.index('        if (!arena->memory)\n        {',s.index('static inline void *horizon_pages_alloc'))
    end=s.index('        if (arena->free_pages < pages)',start)
    s=s[:start]+'        if (!arena->memory) continue;\n'+s[end:]
    anchor='''    return NULL;
}

/* Returns zero for a direct allocation'''
    s=replace(s,anchor,'''    /* Search existing arenas before allocating a new one. A trimmed hole
     * must not hide usable pages in a later arena when libc is exhausted. */
    for(i=0;i<HORIZON_POOL_ARENAS;i++) {
        struct horizon_page_arena *arena=&pool->arenas[i];
        if(arena->memory)continue;
        void *p=aligned_alloc(HORIZON_POOL_PAGE,HORIZON_POOL_PAGES*HORIZON_POOL_PAGE);
        if(!p)return NULL;
        arena->memory=p;arena->free_pages=HORIZON_POOL_PAGES-pages;
        memset(arena->used,0,sizeof(arena->used));memset(arena->used,1,pages);
        pool->misses++;pool->hits++;return p;
    }
    return NULL;
}

/* Returns zero for a direct allocation''')
    p.write_text(s);changed.add('dlls/ntdll/unix/horizon_pool.h')
    return changed
