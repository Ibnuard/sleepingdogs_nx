/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Adapted from Autorun 17a558619724: gather the existing Wine request on the
 * caller's stack and preserve the ordinary pipe path for unsupported calls.
 */
static int horizon_sync_call(struct __server_request_info *req)
{
    union { unsigned long long align; unsigned char bytes[1024]; } data;
    unsigned size = 0;
    if (!horizon_fast_sync_enabled) return 0;
    switch (req->u.req.request_header.req) {
    case REQ_select:
        if (req->u.req.select_request.size > sizeof(data.bytes) - sizeof(union apc_result) ||
            req->u.req.request_header.request_size != sizeof(union apc_result) + req->u.req.select_request.size)
            return 0;
        break;
    case REQ_event_op:
    case REQ_query_event:
    case REQ_release_mutex:
    case REQ_query_mutex:
    case REQ_release_semaphore:
    case REQ_query_semaphore: break;
    default: return 0;
    }
    if (req->u.req.request_header.request_size > sizeof(data.bytes)) return 0;
    if (req->data_count > sizeof(req->data) / sizeof(req->data[0])) return 0;
    for (unsigned i = 0; i < req->data_count; ++i) {
        if (req->data[i].size > sizeof(data.bytes) - size) return 0;
        if (req->data[i].size && !req->data[i].ptr) return 0;
        if (req->data[i].size) memcpy(data.bytes + size, req->data[i].ptr, req->data[i].size);
        size += req->data[i].size;
    }
    if (size != req->u.req.request_header.request_size) return 0;
    return horizon_server_sync_call(HandleToULong(NtCurrentTeb()->ClientId.UniqueThread),
                                    &req->u.req, data.bytes, size, &req->u.reply, req->reply_data);
}
