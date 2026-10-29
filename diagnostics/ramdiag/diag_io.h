/* SPDX-License-Identifier: MIT */
#ifndef HALTIA_DIAG_IO_H
#define HALTIA_DIAG_IO_H
#include <stddef.h>
#include <stdint.h>
#include <sys/types.h>

struct diag_ops {
    long (*now_ms)(void *opaque);
    ssize_t (*read)(int fd,void *data,size_t size,void *opaque);
    ssize_t (*write)(int fd,const void *data,size_t size,void *opaque);
    int (*wait_write)(int fd,int timeout_ms,void *opaque);
    void *opaque;
};
enum { DIAG_LOG_ERROR=1,DIAG_LOG_OVERRUN=2,DIAG_LOG_LIMIT=4 };
extern const struct diag_ops diag_sysops;
long diag_now_ms(void);
int diag_make_raw(int fd);
ssize_t diag_send(int fd,const void *data,size_t size,long deadline_ms,const struct diag_ops *ops);
size_t diag_snapshot(int fd,void *data,size_t capacity,long deadline_ms,unsigned *flags,const struct diag_ops *ops);
uint32_t diag_crc32(const void *data,size_t size);
#endif
