/* SPDX-License-Identifier: MIT */
#include "diag_io.h"
#include <errno.h>
#include <poll.h>
#include <time.h>
#include <termios.h>
#include <unistd.h>

long diag_now_ms(void)
{
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC,&t)) return -1;
    return t.tv_sec*1000+t.tv_nsec/1000000;
}
static long now_impl(void *opaque) { (void)opaque;return diag_now_ms(); }
static ssize_t read_impl(int fd,void *data,size_t size,void *opaque) { (void)opaque;return read(fd,data,size); }
static ssize_t write_impl(int fd,const void *data,size_t size,void *opaque) { (void)opaque;return write(fd,data,size); }
static int wait_impl(int fd,int timeout,void *opaque)
{
    (void)opaque;
    struct pollfd p = { .fd=fd,.events=POLLOUT };
    int rc = poll(&p,1,timeout);
    if (rc > 0 && p.revents&(POLLERR|POLLHUP|POLLNVAL)) { errno=ENODEV;return -1; }
    return rc;
}
const struct diag_ops diag_sysops = { now_impl,read_impl,write_impl,wait_impl,NULL };

int diag_make_raw(int fd)
{
    struct termios settings;
    if (tcgetattr(fd,&settings)) return -1;
    cfmakeraw(&settings);
    settings.c_cflag|=CLOCAL|CREAD;
    return tcsetattr(fd,TCSANOW,&settings);
}

ssize_t diag_send(int fd,const void *data,size_t size,long deadline,const struct diag_ops *ops)
{
    const unsigned char *bytes = data;
    size_t offset = 0;
    for (unsigned calls=0;offset<size && calls<4096;calls++) {
        long now = ops->now_ms(ops->opaque);
        if (now < 0 || now >= deadline) { errno=ETIMEDOUT;return -1; }
        ssize_t n = ops->write(fd,bytes+offset,size-offset,ops->opaque);
        if (n > 0) {
            if ((size_t)n > size-offset) { errno=EIO;return -1; }
            offset += (size_t)n;
        } else if (n < 0 && errno == EINTR) {
            continue;
        } else if (!n || errno == EAGAIN || errno == EWOULDBLOCK) {
            int wait = (int)(deadline-now > 50 ? 50 : deadline-now);
            if (ops->wait_write(fd,wait,ops->opaque) < 0 && errno != EINTR) return -1;
        } else {
            return -1;
        }
    }
    if (offset != size) { errno=ETIMEDOUT;return -1; }
    return (ssize_t)offset;
}

size_t diag_snapshot(int fd,void *data,size_t capacity,long deadline,unsigned *flags,const struct diag_ops *ops)
{
    size_t offset=0;
    *flags=0;
    for (unsigned records=0;records<256;records++) {
        long now = ops->now_ms(ops->opaque);
        if (now < 0) { *flags|=DIAG_LOG_ERROR;return offset; }
        if (now >= deadline || offset == capacity) { *flags|=DIAG_LOG_LIMIT;return offset; }
        size_t available = capacity-offset;
        if (available > 8192) available=8192;
        ssize_t n = ops->read(fd,(unsigned char *)data+offset,available,ops->opaque);
        if (n > 0) {
            if ((size_t)n > available) { *flags|=DIAG_LOG_ERROR;return offset; }
            offset += (size_t)n;
        } else if (!n || errno == EAGAIN || errno == EWOULDBLOCK) {
            return offset;
        } else if (errno == EINTR) {
            continue;
        } else if (errno == EPIPE) {
            *flags|=DIAG_LOG_OVERRUN;
        } else {
            *flags|=DIAG_LOG_ERROR;
            return offset;
        }
    }
    *flags|=DIAG_LOG_LIMIT;
    return offset;
}

uint32_t diag_crc32(const void *data,size_t size)
{
    const unsigned char *p=data;
    uint32_t crc=UINT32_MAX;
    for (size_t i=0;i<size;i++) {
        crc^=p[i];
        for (unsigned bit=0;bit<8;bit++) crc=(crc>>1)^(0xedb88320u&(0u-(crc&1u)));
    }
    return ~crc;
}
