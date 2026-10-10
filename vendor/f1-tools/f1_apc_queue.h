/* LGPL-2.1-or-later. Ordinary user APCs, owned by the target thread object.
 * All queue operations run under horizon_server_objects_mutex. */
#ifndef F1_APC_QUEUE_H
#define F1_APC_QUEUE_H

struct f1_apc_node {
    struct f1_apc_node *next;
    struct user_apc call;
};
struct f1_apc_queue {
    struct f1_apc_node *head, *tail;
};

static unsigned int f1_apc_push(struct f1_apc_queue *queue, const struct user_apc *call)
{
    struct f1_apc_node *node = malloc(sizeof(*node));
    if (!node) return STATUS_NO_MEMORY;
    node->next = NULL;
    node->call = *call;
    if (queue->tail) queue->tail->next = node;
    else queue->head = node;
    queue->tail = node;
    return STATUS_SUCCESS;
}

static int f1_apc_pop(struct f1_apc_queue *queue, union apc_call *out)
{
    struct f1_apc_node *node = queue->head;
    if (!node) return 0;
    memset(out, 0, sizeof(*out));
    out->user = node->call;
    queue->head = node->next;
    if (!queue->head) queue->tail = NULL;
    free(node);
    return 1;
}

static void f1_apc_clear(struct f1_apc_queue *queue)
{
    union apc_call unused;
    while (f1_apc_pop(queue, &unused)) {}
}
#endif
