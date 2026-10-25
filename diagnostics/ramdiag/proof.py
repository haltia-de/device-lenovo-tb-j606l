#!/usr/bin/env python3
"""Offline parser: Linux/PID1 proof requires a complete CRC-framed early log."""
import re
import zlib

MAX_LOG_BYTES=65536
MAX_CAPTURE_BYTES=4*1024*1024
MODEL=b'Lenovo Tab P11 TB-J606L RAM diagnostic'


def verify(data,build_id,release):
    if len(data)>MAX_CAPTURE_BYTES:
        raise ValueError('Host capture exceeds reviewed bound.')
    if not re.fullmatch(r'haltia-j606l-[0-9a-f]{16}',build_id):
        raise ValueError('Invalid artifact-bound build ID.')
    token=re.escape(build_id.encode())
    version=re.escape(release.encode())
    kernel=re.search(rb'(?m)^HALTIA_J606L_KERNEL build='+token+rb' sysname=Linux release='+version+rb' machine=aarch64\r?$',data)
    init=re.search(rb'(?m)^HALTIA_J606L_INIT build='+token+rb' pid=1 rootfs_magic=(0x[0-9a-fA-F]+) model='+re.escape(MODEL)+rb'\r?$',data)
    policy=b'HALTIA_J606L_POLICY block_support=disabled mdss=disabled persistent_mounts=none' in data
    if not kernel or not init or not policy:
        raise ValueError('Kernel/PID1/RAM/no-storage proof incomplete.')
    if int(init.group(1),16) not in (0x858458f6,0x01021994):
        raise ValueError('Root filesystem is not RAMFS/TMPFS.')
    header=re.compile(rb'(?m)^HALTIA_J606L_KMSG_BEGIN build='+token+rb' bytes=([0-9]+) crc32=([0-9a-f]{8}) flags=([0-9]+)\n')
    for match in header.finditer(data):
        size=int(match.group(1))
        flags=int(match.group(3))
        if not 0<size<=MAX_LOG_BYTES or flags>7:
            continue
        start=match.end()
        end=start+size
        trailer=b'\nHALTIA_J606L_KMSG_END build='+build_id.encode()+b' bytes='+str(size).encode()+b'\n'
        if data[end:end+len(trailer)]!=trailer:
            continue
        body=data[start:end]
        if zlib.crc32(body)!=int(match.group(2),16):
            continue
        if b'Linux version '+release.encode() not in body:
            continue
        return dict(kernel_proof=True,pid1_proof=True,ram_root=True,no_storage_policy_reported=True,
                    early_kernel_log_crc_valid=True,early_kernel_log_bytes=size,early_kernel_log_flags=flags,
                    early_kernel_log_partial=bool(flags),build_id=build_id,release=release)
    raise ValueError('Complete byte-exact early-kernel-log frame missing.')
