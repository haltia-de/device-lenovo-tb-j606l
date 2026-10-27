#!/usr/bin/env python3
"""Shrink userdata on UFS LUN 0 and add a "haltia" Linux partition after it.

Input: the current primary GPT of LUN 0 as read over EDL (sectors 0..5,
4096-byte sectors). Output: primary.bin (sectors 1..2) and backup.bin
(the last two sectors of the LUN), ready for `qdl write`.
"""
import argparse
import struct
import uuid
import zlib

SS = 4096
LINUX_FS = uuid.UUID('0fc63daf-8483-4772-8e79-3d69d8477de4')


def crc(data):
    return zlib.crc32(data) & 0xffffffff


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('gpt', help='LUN 0 sectors 0..5 from the device')
    ap.add_argument('--userdata-gib', type=int, default=64)
    ap.add_argument('--out', default='.')
    a = ap.parse_args()
    d = open(a.gpt, 'rb').read()
    hdr = bytearray(d[SS:SS + 92])
    if hdr[:8] != b'EFI PART':
        raise SystemExit('no primary GPT header')
    cur, alt, first, last = struct.unpack_from('<QQQQ', hdr, 24)
    ent_lba, n, esz = struct.unpack_from('<QII', hdr, 72)
    if (cur, ent_lba, n, esz) != (1, 2, 32, 128):
        raise SystemExit('unexpected GPT geometry')
    ents = bytearray(d[ent_lba * SS:ent_lba * SS + n * esz])
    names = {}
    for i in range(n):
        e = ents[i * esz:(i + 1) * esz]
        if e[:16] != b'\0' * 16:
            names[e[56:128].decode('utf-16le').rstrip('\0')] = i
    if 'haltia' in names:
        raise SystemExit('haltia partition already present')
    u = names['userdata']
    uf, ul = struct.unpack_from('<QQ', ents, u * esz + 32)
    if ul != last:
        raise SystemExit('userdata is not the last partition')
    new_ul = uf + a.userdata_gib * (1 << 30) // SS - 1
    if new_ul >= last - (4 << 30) // SS:
        raise SystemExit('no room for the Linux partition')
    struct.pack_into('<Q', ents, u * esz + 40, new_ul)
    free = next(i for i in range(n) if ents[i * esz:i * esz + 16] == b'\0' * 16)
    e = bytearray(esz)
    e[0:16] = LINUX_FS.bytes_le
    e[16:32] = uuid.uuid4().bytes_le
    struct.pack_into('<QQQ', e, 32, new_ul + 1, last, 0)
    e[56:56 + 12] = 'haltia'.encode('utf-16le')
    ents[free * esz:(free + 1) * esz] = e
    ecrc = crc(bytes(ents))

    def header(this, other, entries_at):
        h = bytearray(hdr)
        struct.pack_into('<QQ', h, 24, this, other)
        struct.pack_into('<Q', h, 72, entries_at)
        struct.pack_into('<I', h, 88, ecrc)
        struct.pack_into('<I', h, 16, 0)
        struct.pack_into('<I', h, 16, crc(bytes(h)))
        return bytes(h) + b'\0' * (SS - len(h))

    table = bytes(ents) + b'\0' * (SS - len(ents))
    open(f'{a.out}/primary.bin', 'wb').write(header(1, alt, 2) + table)
    open(f'{a.out}/backup.bin', 'wb').write(table + header(alt, 1, alt - 1))
    print(f'userdata {uf}..{new_ul} ({(new_ul - uf + 1) * SS / 2**30:.1f} GiB)')
    print(f'haltia   {new_ul + 1}..{last} ({(last - new_ul) * SS / 2**30:.1f} GiB), entry {free}')
    print(f'write primary.bin at 0/1+2, backup.bin at 0/{alt - 1}+2')


if __name__ == '__main__':
    main()
