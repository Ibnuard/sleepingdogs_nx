/* Included in horizon.c, after fd I/O and before backing lifetime helpers. */
static void *horizon_backing_pages_alloc(size_t size)
{
    void *ptr = horizon_pages_alloc(&backing_pages, size);
    if (!ptr) { ptr = memalign(0x1000, size); backing_direct_allocs++; }
    return ptr;
}
static void horizon_backing_pages_free(void *ptr, size_t size)
{
    if (!horizon_pages_free(&backing_pages, ptr, size)) free(ptr);
}
static int horizon_backing_io(struct horizon_backing *backing, int fd, off_t offset, int write)
{
    size_t at = 0, size;
    while (at < backing->size) {
        void *ptr = horizon_store_at(&backing->pages, at, &size);
        if (write) write_fd_at(fd, ptr, size, offset + at);
        else if (read_fd_at(fd, ptr, size, offset + at)) return -1;
        at += size;
    }
    return 0;
}
static int map_code_memory_range_ex(void *, void *, size_t, int, int, unsigned *);
static int unmap_code_memory_range(void *, void *, size_t);
static int set_code_memory_perm(void *, void *, size_t, int, BOOL);
struct horizon_store_map_context {
    struct horizon_backing *backing;
    int prot, old_prot, map_errno;
};
static int horizon_store_map_piece(void *addr, void *src, size_t size, void *arg)
{
    struct horizon_store_map_context *c = arg;
    return map_code_memory_range_ex(addr, src, size, c->prot, c->map_errno,
                                   &c->backing->pages.poisoned);
}
static int horizon_store_unmap_piece(void *addr, void *src, size_t size, void *arg)
{
    (void)arg;
    return unmap_code_memory_range(addr, src, size);
}
static int horizon_backing_map(struct horizon_backing *b, void *addr, size_t off,
                               size_t size, int prot, int map_errno)
{
    struct horizon_store_map_context c = {b, prot, prot, map_errno};
    return horizon_store_range(&b->pages, addr, off, size, horizon_store_map_piece,
                               horizon_store_unmap_piece, &c);
}
static int horizon_backing_unmap(struct horizon_backing *b, void *addr, size_t off,
                                 size_t size, int prot)
{
    struct horizon_store_map_context c = {b, prot, prot, EINVAL};
    return horizon_store_range(&b->pages, addr, off, size, horizon_store_unmap_piece,
                               horizon_store_map_piece, &c);
}
static int horizon_store_perm_piece(void *addr, void *src, size_t size, void *arg)
{
    struct horizon_store_map_context *c = arg;
    return set_code_memory_perm(addr, src, size, c->prot, FALSE);
}
static int horizon_store_old_perm_piece(void *addr, void *src, size_t size, void *arg)
{
    struct horizon_store_map_context *c = arg;
    return set_code_memory_perm(addr, src, size, c->old_prot, FALSE);
}
static int horizon_backing_protect(struct horizon_mapping *mapping, int prot)
{
    struct horizon_store_map_context c = {mapping->backing, prot, mapping->prot, EINVAL};
    return horizon_store_range(&mapping->backing->pages, mapping->addr,
        mapping->source_offset, mapping->size, horizon_store_perm_piece,
        horizon_store_old_perm_piece, &c);
}
void wine_nx_page_store_snapshot(uint64_t out[8])
{
    for (unsigned i = 0; i < 8; ++i)
        out[i] = __atomic_load_n(&horizon_store_stats[i], __ATOMIC_RELAXED);
}
