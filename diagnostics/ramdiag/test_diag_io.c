/* SPDX-License-Identifier: MIT */
/* Native host-only tests: fake I/O and private PTYs; never link or execute PID1. */
#include "diag_io.h"
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <pty.h>
#include <stdio.h>
#include <string.h>
#include <termios.h>
#include <unistd.h>

struct fake { long time; unsigned calls,waits,reads; int mode; unsigned char output[256];size_t used; };
static long clock_fake(void *p) { struct fake *s=p;return s->time++; }
static int wait_fake(int fd,int ms,void *p) { (void)fd;struct fake *s=p;s->time+=ms;s->waits++;return 1; }
static ssize_t write_fake(int fd,const void *data,size_t size,void *p)
{
    (void)fd;struct fake *s=p;s->calls++;
    if (s->mode==1 || (s->mode==0 && s->calls==2)) { errno=EAGAIN;return -1; }
    if (s->mode==2) return 0;
    if (s->mode==3) { errno=EIO;return -1; }
    if (s->mode==0 && s->calls==1) { errno=EINTR;return -1; }
    size_t n=size>3?3:size;
    assert(s->used+n<=sizeof(s->output));
    memcpy(s->output+s->used,data,n);s->used+=n;return (ssize_t)n;
}
static ssize_t read_fake(int fd,void *data,size_t size,void *p)
{
    (void)fd;struct fake *s=p;s->reads++;
    if (s->mode==4) { errno=EPIPE;return -1; }
    if (s->mode==5 && s->reads==1) { errno=EPIPE;return -1; }
    if (s->reads>2) { errno=EAGAIN;return -1; }
    const unsigned char value[]={'A','\n','B','\r',0,'C'};
    size_t n=size>sizeof(value)?sizeof(value):size;
    memcpy(data,value,n);return (ssize_t)n;
}

int main(void)
{
    const unsigned char bytes[]={'a','\n','b','\r',0,'c','\n'};
    struct fake state={0};
    struct diag_ops ops={clock_fake,read_fake,write_fake,wait_fake,&state};
    assert(diag_send(1,bytes,sizeof(bytes),1000,&ops)==(ssize_t)sizeof(bytes));
    assert(state.calls>3 && state.waits==1 && state.used==sizeof(bytes));
    assert(!memcmp(state.output,bytes,sizeof(bytes)));
    for (int mode=1;mode<=3;mode++) {
        memset(&state,0,sizeof(state));state.mode=mode;
        assert(diag_send(1,bytes,sizeof(bytes),60,&ops)==-1);
        assert(state.calls<=3 && state.waits<=2);
    }
    unsigned char snapshot[32];unsigned flags;
    memset(&state,0,sizeof(state));
    size_t got=diag_snapshot(1,snapshot,sizeof(snapshot),1000,&flags,&ops);
    assert(got==12 && flags==0 && state.reads==3);
    memset(&state,0,sizeof(state));state.mode=5;
    got=diag_snapshot(1,snapshot,sizeof(snapshot),1000,&flags,&ops);
    assert(got==6 && flags==DIAG_LOG_OVERRUN);
    memset(&state,0,sizeof(state));state.mode=4;
    got=diag_snapshot(1,snapshot,sizeof(snapshot),10000,&flags,&ops);
    assert(!got && state.reads==256 && flags==(DIAG_LOG_OVERRUN|DIAG_LOG_LIMIT));
    memset(&state,0,sizeof(state));
    got=diag_snapshot(1,snapshot,5,1000,&flags,&ops);
    assert(got==5 && flags==DIAG_LOG_LIMIT);
    memset(&state,0,sizeof(state));state.mode=4;
    got=diag_snapshot(1,snapshot,sizeof(snapshot),3,&flags,&ops);
    assert(!got && state.reads<=3 && (flags&DIAG_LOG_LIMIT));
    assert(diag_crc32("123456789",9)==0xcbf43926u);
    /* Two PTY pairs model device output discipline and host input discipline.
     * The bridge masters are never configured; only the actual endpoints are.
     */
    int m1,s1,m2,s2;
    assert(!openpty(&m1,&s1,NULL,NULL,NULL));
    assert(!openpty(&m2,&s2,NULL,NULL,NULL));
    assert(!diag_make_raw(s1) && !diag_make_raw(s2));
    struct termios settings;
    assert(!tcgetattr(s1,&settings) && !(settings.c_oflag&OPOST));
    assert(!tcgetattr(s2,&settings) && !(settings.c_iflag&(ICRNL|INLCR|IGNCR)));
    assert(!fcntl(s1,F_SETFL,O_NONBLOCK));
    assert(diag_send(s1,bytes,sizeof(bytes),diag_now_ms()+1000,&diag_sysops)==(ssize_t)sizeof(bytes));
    unsigned char bridge[64],received[64];
    ssize_t n=read(m1,bridge,sizeof(bridge));
    assert(n==(ssize_t)sizeof(bytes) && !memcmp(bridge,bytes,sizeof(bytes)));
    assert(write(m2,bridge,(size_t)n)==n);
    n=read(s2,received,sizeof(received));
    assert(n==(ssize_t)sizeof(bytes) && !memcmp(received,bytes,sizeof(bytes)));
    assert(diag_crc32(received,(size_t)n)==diag_crc32(bytes,sizeof(bytes)));
    close(m1);close(s1);close(m2);close(s2);
    assert(diag_make_raw(-1)==-1);
    puts("PASS: short writes/EAGAIN/deadlines, snapshot bounds/overrun, real raw PTYs LF/CR/NUL, CRC.");
    return 0;
}
