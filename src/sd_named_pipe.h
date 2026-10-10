/* SPDX-License-Identifier: LGPL-2.1-or-later */
#ifndef SD_NAMED_PIPE_H
#define SD_NAMED_PIPE_H
/* Private native Wine interface. FALSE means this is not one of our handles. */
NTSTATUS sd_pipe_create(HANDLE *, ULONG, OBJECT_ATTRIBUTES *, IO_STATUS_BLOCK *,
                       ULONG, ULONG, ULONG, ULONG, ULONG, ULONG, ULONG, ULONG, ULONG);
BOOL sd_pipe_open(HANDLE *, ULONG, OBJECT_ATTRIBUTES *, IO_STATUS_BLOCK *, ULONG, ULONG, NTSTATUS *);
BOOL sd_pipe_read_write(HANDLE, HANDLE, PIO_APC_ROUTINE, void *, IO_STATUS_BLOCK *,
                        void *, ULONG, BOOL, NTSTATUS *);
BOOL sd_pipe_control(HANDLE, HANDLE, PIO_APC_ROUTINE, void *, IO_STATUS_BLOCK *,
                     ULONG, void *, ULONG, NTSTATUS *);
BOOL sd_pipe_query(HANDLE, IO_STATUS_BLOCK *, void *, ULONG, ULONG, NTSTATUS *);
BOOL sd_pipe_set(HANDLE, IO_STATUS_BLOCK *, void *, ULONG, ULONG, NTSTATUS *);
BOOL sd_pipe_volume(HANDLE, IO_STATUS_BLOCK *, void *, ULONG, ULONG, NTSTATUS *);
BOOL sd_pipe_cancel(HANDLE, IO_STATUS_BLOCK *, IO_STATUS_BLOCK *, BOOL, NTSTATUS *);
#endif
