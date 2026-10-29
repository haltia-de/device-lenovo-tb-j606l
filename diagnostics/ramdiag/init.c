/* SPDX-License-Identifier: MIT */
/* PID1 for a bounded RAM-only Linux proof over USB ACM. No block-device code. */
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/reboot.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/syscall.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <sys/types.h>
#include <sys/utsname.h>
#include <termios.h>
#include <unistd.h>
#include "diag_io.h"

#ifndef DIAG_BUILD_ID
#error "A manifest-bound build ID is required."
#endif

static int put(const char *path, const char *value)
{
    int fd = open(path,O_WRONLY|O_CLOEXEC);
    if (fd < 0) return -1;
    size_t size = strlen(value);
    ssize_t n = write(fd,value,size);
    int closed = close(fd);
    return n == (ssize_t)size && !closed ? 0 : -1;
}

static int directory(const char *path)
{
    return mkdir(path,0755) == 0 || errno == EEXIST ? 0 : -1;
}

static void text(const char *path,char *buf,size_t size)
{
    int fd = open(path,O_RDONLY|O_CLOEXEC);
    if (fd < 0) { snprintf(buf,size,"unavailable"); return; }
    ssize_t n = read(fd,buf,size-1);
    close(fd);
    if (n < 0) n = 0;
    buf[n] = 0;
    for (ssize_t i = 0; i < n; i++) if (buf[i] == '\n' || buf[i] == '\r') buf[i] = ' ';
}

static int udc(char *name,size_t size)
{
    DIR *dir = opendir("/sys/class/udc");
    struct dirent *entry;
    unsigned count = 0;
    if (!dir) return -1;
    while ((entry = readdir(dir))) {
        if (entry->d_name[0] == '.') continue;
        if (strlen(entry->d_name) >= size) { closedir(dir); return -1; }
        snprintf(name,size,"%s",entry->d_name);
        count++;
    }
    closedir(dir);
    return count == 1 ? 0 : -1;
}

static int gadget(const char *controller)
{
    const char *root = "/sys/kernel/config/usb_gadget/j606l_ramdiag";
    if (directory(root) || chdir(root)) return -1;
    if (put("idVendor","0x1d6b") || put("idProduct","0x0104") ||
        directory("strings/0x409") || put("strings/0x409/manufacturer","Haltia diagnostic") ||
        put("strings/0x409/product","TB-J606L RAM Linux proof") ||
        put("strings/0x409/serialnumber",DIAG_BUILD_ID) ||
        directory("configs/c.1") || directory("configs/c.1/strings/0x409") ||
        put("configs/c.1/strings/0x409/configuration","RAM proof ACM only") ||
        directory("functions/acm.usb0") || symlink("../../functions/acm.usb0","configs/c.1/acm.usb0") ||
        put("UDC",controller)) return -1;
    return 0;
}

int main(void)
{
    /* Everything written below is a RAM filesystem or USB gadget configfs.
     * CONFIG_BLOCK=n is an independent build-time condition, checked offline.
     */
    if (getpid() != 1) return 126;
    umask(077);
    long started = diag_now_ms();
    if (started < 0) goto return_bootloader;
    long deadline = started+90000;
    directory("/proc"); directory("/sys"); directory("/dev");
    if (mount("proc","/proc","proc",MS_NOSUID|MS_NODEV|MS_NOEXEC,NULL) ||
        mount("sysfs","/sys","sysfs",MS_NOSUID|MS_NODEV|MS_NOEXEC,NULL) ||
        mount("devtmpfs","/dev","devtmpfs",MS_NOSUID,"mode=0755")) goto return_bootloader;
    if (directory("/sys/kernel/config") || mount("configfs","/sys/kernel/config","configfs",MS_NOSUID|MS_NODEV|MS_NOEXEC,NULL)) goto return_bootloader;
    char controller[256] = {0};
    int controller_ready = -1;
    for (unsigned attempt = 0; attempt < 20; attempt++) {
        controller_ready = udc(controller,sizeof(controller));
        if (!controller_ready) break;
        sleep(1);
    }
    if (controller_ready || gadget(controller)) goto return_bootloader;
    struct utsname kernel;
    struct statfs rootfs;
    char model[256],message[2048];
    if (uname(&kernel) || statfs("/",&rootfs)) goto return_bootloader;
    text("/proc/device-tree/model",model,sizeof(model));
    static unsigned char kernel_log[65536];
    size_t log_bytes=0;
    unsigned log_flags=DIAG_LOG_ERROR;
    int logfd=open("/dev/kmsg",O_RDONLY|O_NONBLOCK|O_CLOEXEC);
    if (logfd >= 0) {
        long until=diag_now_ms()+1000;
        if (until>deadline) until=deadline;
        log_bytes=diag_snapshot(logfd,kernel_log,sizeof(kernel_log),until,&log_flags,&diag_sysops);
        close(logfd);
    }
    uint32_t log_crc=diag_crc32(kernel_log,log_bytes);
    char log_header[256],log_end[192];
    int header_size=snprintf(log_header,sizeof(log_header),
        "HALTIA_J606L_KMSG_BEGIN build=%s bytes=%zu crc32=%08x flags=%u\n",DIAG_BUILD_ID,log_bytes,log_crc,log_flags);
    int end_size=snprintf(log_end,sizeof(log_end),
        "\nHALTIA_J606L_KMSG_END build=%s bytes=%zu\n",DIAG_BUILD_ID,log_bytes);
    if (header_size<=0 || header_size>=(int)sizeof(log_header) || end_size<=0 || end_size>=(int)sizeof(log_end)) goto return_bootloader;
    int length = snprintf(message,sizeof(message),
        "HALTIA_J606L_KERNEL build=%s sysname=%s release=%s machine=%s\n"
        "HALTIA_J606L_INIT build=%s pid=%ld rootfs_magic=0x%lx model=%s\n"
        "HALTIA_J606L_POLICY block_support=disabled mdss=disabled persistent_mounts=none\n",
        DIAG_BUILD_ID,kernel.sysname,kernel.release,kernel.machine,
        DIAG_BUILD_ID,(long)getpid(),(unsigned long)rootfs.f_type,model);
    if (length <= 0 || length >= (int)sizeof(message)) goto return_bootloader;
    for (unsigned frame = 0; frame < 45 && diag_now_ms()>=0 && diag_now_ms()<deadline; frame++) {
        int fd = open("/dev/ttyGS0",O_WRONLY|O_NOCTTY|O_NONBLOCK|O_CLOEXEC);
        if (fd >= 0) {
            if (diag_make_raw(fd)) { close(fd);goto return_bootloader; }
            /* One bounded sender handles short writes/EAGAIN for proof and
             * log framing alike. Raw kmsg remains in RAM and private capture.
             */
            struct { const void *data; size_t size; } chunks[] = {
                { message,(size_t)length }, { log_header,(size_t)header_size },
                { kernel_log,log_bytes }, { log_end,(size_t)end_size }
            };
            int complete=1;
            for (unsigned i=0;i<sizeof(chunks)/sizeof(chunks[0]);i++) {
                if (diag_send(fd,chunks[i].data,chunks[i].size,deadline,&diag_sysops)!=(ssize_t)chunks[i].size) { complete=0;break; }
            }
            close(fd);
            if (!complete && diag_now_ms()>=deadline) break;
        }
        sleep(2);
    }
return_bootloader:
    /* PM6125 mode-bootloader=2 + qcom-pon reboot-mode implements this request.
     * It is not an assertion of production bootloader behavior or a return to
     * Android B. The host must observe fastboot, select B and verify Android.
     * There is no RB_AUTOBOOT fallback or repeated request if this fails.
     */
    (void)syscall(SYS_reboot,LINUX_REBOOT_MAGIC1,LINUX_REBOOT_MAGIC2,
                  LINUX_REBOOT_CMD_RESTART2,"bootloader");
    for (;;) pause();
}
