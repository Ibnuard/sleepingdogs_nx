/* LGPL-2.1-or-later. Horizon has no Linux syscall_frame. Allocate the same
 * ARM64 APC frame as Wine below the active native stack, then enter the PE
 * KiUserApcDispatcher with x18 bound to the TEB. Wow64ApcRoutine builds the
 * x86 APC frame and uses the existing FEX context bridge; NtContinue restores
 * this continuation after the x86 completion routine returns.
 *
 * In particular, never call a guest x86 callback as a native function and
 * never put the APC frame above the current SP (it would overwrite C frames).
 */
struct f1_arm64_apc_frame {
    PNTAPCFUNC func;
    ULONG_PTR args[3];
    ULONG64 alertable, pad;
    CONTEXT context;
};
C_ASSERT(offsetof(struct f1_arm64_apc_frame, context) == 0x30);
C_ASSERT(sizeof(struct f1_arm64_apc_frame) == 0x3c0);
C_ASSERT(offsetof(CONTEXT, X18) == 0x98);
C_ASSERT(offsetof(CONTEXT, X19) == 0xa0);
C_ASSERT(offsetof(CONTEXT, Fp) == 0xf0);
C_ASSERT(offsetof(CONTEXT, Sp) == 0x100);
C_ASSERT(offsetof(CONTEXT, Pc) == 0x108);
C_ASSERT(offsetof(CONTEXT, V) == 0x110);
C_ASSERT(offsetof(CONTEXT, Fpcr) == 0x310);

extern NTSTATUS f1_enter_apc(const struct f1_arm64_apc_frame *, void *, TEB *, NTSTATUS, int);
extern unsigned long long f1_apc_entered, f1_apc_returned;
__asm__(
    ".global f1_enter_apc\n"
    ".type f1_enter_apc, %function\n"
    "f1_enter_apc:\n"
    "    hint 34\n"
    "    mrs x14, nzcv\n"
    "    sub x15, sp, #0x3c0\n"
    /* NtContinue drains further APCs on the original continuation stack.
     * Reuse that frame instead of growing the native stack for every item. */
    "    cbnz w4, 1f\n"
    "    ldr x15, [x0, #0x130]\n"
    "    and x15, x15, #-16\n"
    "    sub x15, x15, #0x3c0\n"
    "1:\n"
    "    mov x9, x0\n"
    "    mov x10, x15\n"
    "    mov x11, #0x3c0\n"
    /* memmove: explicit contexts can place the frame above the source. */
    "    cmp x10, x9\n"
    "    b.ls 2f\n"
    "    add x9, x9, x11\n"
    "    add x10, x10, x11\n"
    "1:  ldp x12, x13, [x9, #-16]!\n"
    "    stp x12, x13, [x10, #-16]!\n"
    "    subs x11, x11, #16\n"
    "    b.ne 1b\n"
    "    b 3f\n"
    "2:  ldp x12, x13, [x9], #16\n"
    "    stp x12, x13, [x10], #16\n"
    "    subs x11, x11, #16\n"
    "    b.ne 2b\n"
    "3:  mov sp, x15\n"
    "    cbz w4, 4f\n"
    /* A normal C call only promises to preserve the nonvolatile registers.
     * X0 supplies the wait result; the other volatile slots are zeroed by C. */
    "    add x9, sp, #0x30\n"
    "    str w14, [x9, #4]\n"
    "    sxtw x3, w3\n"
    "    str x3, [x9, #8]\n"
    "    str x18, [x9, #0x98]\n"
    "    stp x19, x20, [x9, #0xa0]\n"
    "    stp x21, x22, [x9, #0xb0]\n"
    "    stp x23, x24, [x9, #0xc0]\n"
    "    stp x25, x26, [x9, #0xd0]\n"
    "    stp x27, x28, [x9, #0xe0]\n"
    "    stp x29, x30, [x9, #0xf0]\n"
    "    add x10, sp, #0x3c0\n"
    "    stp x10, x30, [x9, #0x100]\n"
    "    stp q0, q1, [x9, #0x110]\n"
    "    stp q2, q3, [x9, #0x130]\n"
    "    stp q4, q5, [x9, #0x150]\n"
    "    stp q6, q7, [x9, #0x170]\n"
    "    stp q8, q9, [x9, #0x190]\n"
    "    stp q10, q11, [x9, #0x1b0]\n"
    "    stp q12, q13, [x9, #0x1d0]\n"
    "    stp q14, q15, [x9, #0x1f0]\n"
    "    stp q16, q17, [x9, #0x210]\n"
    "    stp q18, q19, [x9, #0x230]\n"
    "    stp q20, q21, [x9, #0x250]\n"
    "    stp q22, q23, [x9, #0x270]\n"
    "    stp q24, q25, [x9, #0x290]\n"
    "    stp q26, q27, [x9, #0x2b0]\n"
    "    stp q28, q29, [x9, #0x2d0]\n"
    "    stp q30, q31, [x9, #0x2f0]\n"
    "    mrs x10, fpcr\n"
    "    str w10, [x9, #0x310]\n"
    "    mrs x10, fpsr\n"
    "    str w10, [x9, #0x314]\n"
    "4:  mov x18, x2\n"
    "    br x1\n"
    ".size f1_enter_apc, . - f1_enter_apc\n"
);

NTSTATUS call_user_apc_dispatcher(CONTEXT *context, unsigned int flags,
                                 ULONG_PTR arg1, ULONG_PTR arg2, ULONG_PTR arg3,
                                 PNTAPCFUNC func, NTSTATUS status)
{
    struct f1_arm64_apc_frame frame = {0};
    NTSTATUS result;
    if (flags) return STATUS_NOT_SUPPORTED;
    if (!func || !pKiUserApcDispatcher) return STATUS_INVALID_PARAMETER;
    if (context) {
        if ((context->ContextFlags & CONTEXT_ARM64_FULL) != CONTEXT_ARM64_FULL ||
            context->Sp < sizeof(frame))
            return STATUS_INVALID_PARAMETER;
        frame.context = *context;
    } else frame.context.ContextFlags = CONTEXT_FULL | CONTEXT_ARM64_X18;
    frame.func = func;
    frame.args[0] = arg1; frame.args[1] = arg2; frame.args[2] = arg3;
    frame.alertable = TRUE;
    __atomic_add_fetch(&f1_apc_entered, 1, __ATOMIC_RELAXED);
    result = f1_enter_apc(&frame, pKiUserApcDispatcher, NtCurrentTeb(), status, !context);
    /* NtContinue with an explicit context resumes that context instead of
     * returning here. This counts completed outer dispatches, not callbacks. */
    __atomic_add_fetch(&f1_apc_returned, 1, __ATOMIC_RELAXED);
    return result;
}
