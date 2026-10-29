#!/usr/bin/env python3
"""Offline deterministic packaging only. No flashing or device access."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import stat
import struct
import subprocess
import tempfile
import sys
import zlib

import build

HERE=Path(__file__).resolve().parent
STOCK_CONTROL=json.loads((HERE/'stock-header.json').read_text())
STOCK_SHA=STOCK_CONTROL['stock_boot_b_sha256']
MKBOOTIMG_SHA='5579fb6bcb9e89e790a70fb9ccf3c00cf56e3e46aef74d84fcb0964887e5576e'
OS_WORD=0x16000177


def newc(init):
    data=bytearray()
    entries=[('.',stat.S_IFDIR|0o755,b'',0,0),('dev',stat.S_IFDIR|0o755,b'',0,0),
             ('dev/console',stat.S_IFCHR|0o600,b'',5,1),
             ('init',stat.S_IFREG|0o755,init,0,0),('TRAILER!!!',0,b'',0,0)]
    for inode,(name,mode,payload,major,minor) in enumerate(entries,1):
        encoded=name.encode()+b'\0'
        fields=(inode,mode,0,0,2 if stat.S_ISDIR(mode) else 1,0,len(payload),0,0,major,minor,len(encoded),0)
        data.extend(b'070701'+b''.join(f'{x:08x}'.encode() for x in fields)+encoded)
        data.extend(b'\0'*(-len(data)%4));data.extend(payload);data.extend(b'\0'*(-len(data)%4))
    data.extend(b'\0'*(-len(data)%512))
    return bytes(data)


def header(data):
    if len(data)<1660 or data[:8]!=b'ANDROID!':raise ValueError('Invalid Android header.')
    names=('kernel_size','kernel_addr','ramdisk_size','ramdisk_addr','second_size','second_addr',
           'tags_addr','page_size','header_version','os_version_word')
    result=dict(zip(names,struct.unpack_from('<10I',data,8)))
    result.update(header_size=struct.unpack_from('<I',data,1644)[0],
                  dtb_size=struct.unpack_from('<I',data,1648)[0],dtb_addr=struct.unpack_from('<Q',data,1652)[0])
    return result


def check_header(candidate,stock):
    fixed=dict(kernel_addr=0x8000,ramdisk_addr=0x1000000,second_size=0,second_addr=0,tags_addr=0x100,
               page_size=4096,header_version=2,header_size=1660,dtb_addr=0x1f00000,os_version_word=OS_WORD)
    for key,value in fixed.items():
        if stock[key]!=value or candidate[key]!=value:raise ValueError('Stock-compatible header mismatch: '+key)


def pack(out,init,kernel,dtb):
    ramdisk=out/'initramfs.cpio.gz'
    ramdisk.write_bytes(gzip.compress(newc(init),compresslevel=9,mtime=0))
    image=out/'boot-j606l-ramdiag.img'
    args=['--kernel',str(kernel),'--ramdisk',str(ramdisk),'--dtb',str(dtb),
          '--header_version','2','--pagesize','4096','--base','0',
          '--kernel_offset','0x8000','--ramdisk_offset','0x1000000','--second_offset','0',
          '--tags_offset','0x100','--dtb_offset','0x1f00000',
          '--os_version','11.0.0','--os_patch_level','2023-07','--output',str(image)]
    subprocess.run(['rtk','proxy','python3',str(HERE/'mkbootimg.py'),*args],check=True,capture_output=True,timeout=30)
    return image,ramdisk,args


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work',type=Path,required=True)
    args=parser.parse_args();work=args.work.resolve()
    if work==HERE or work.is_relative_to(HERE):parser.error('--work must be outside the publishable tree.')
    os.umask(0o077)
    manifest=json.loads((work/'kernel-build.private.json').read_text())
    if build.sha(HERE/'mkbootimg.py')!=MKBOOTIMG_SHA:
        raise ValueError('Pinned stock/control source changed.')
    for name,digest in manifest['input_hashes'].items():
        if build.sha(HERE/name)!=digest:raise ValueError('Kernel build input changed: '+name)
    out=work/'build';init=out/'ramdiag-userspace/init';kernel=out/'arch/arm64/boot/Image.gz'
    dtb=out/f'arch/arm64/boot/dts/qcom/{build.TARGET}.dtb'
    for path,key in ((init,'init_binary_sha256'),(kernel,'image_gz_sha256'),(dtb,'dtb_sha256'),(out/'.config','config_sha256')):
        if build.sha(path)!=manifest[key]:raise ValueError('Built artifact changed.')
    build.check_config(out/'.config');build.check_init_elf(init)
    destination=work/'package';destination.mkdir(mode=0o700,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=work,prefix='pack-check-') as tmp:
        image,ramdisk,args=pack(destination,init.read_bytes(),kernel,dtb)
        second,second_ramdisk,_=pack(Path(tmp),init.read_bytes(),kernel,dtb)
        if image.read_bytes()!=second.read_bytes() or ramdisk.read_bytes()!=second_ramdisk.read_bytes():
            raise ValueError('Packaging is not reproducible.')
    candidate=header(image.read_bytes());stock=STOCK_CONTROL['header'];check_header(candidate,stock)
    if (candidate['kernel_size'],candidate['ramdisk_size'],candidate['dtb_size'])!=(kernel.stat().st_size,ramdisk.stat().st_size,dtb.stat().st_size):
        raise ValueError('Component size mismatch.')
    result=dict(build_id=manifest['build_id'],kernel_release=(out/'include/config/kernel.release').read_text().strip(),
        packaging_runtime=dict(python=sys.version.split()[0],zlib_compile=zlib.ZLIB_VERSION,zlib_runtime=zlib.ZLIB_RUNTIME_VERSION),
        kernel_build_manifest_sha256=build.sha(work/'kernel-build.private.json'),
        stock_boot_b_sha256=STOCK_SHA,mkbootimg_source_sha256=MKBOOTIMG_SHA,
        boot_image_sha256=build.sha(image),boot_image_bytes=image.stat().st_size,
        initramfs_sha256=build.sha(ramdisk),initramfs_bytes=ramdisk.stat().st_size,
        candidate_header=candidate,stock_header=stock,packaged_twice_identical=True,
        boot_os_version='11.0.0',boot_security_patch='2023-07',rollback_metadata_added=False,
        mkbootimg_args=args,hardware_tested=False,bootloader_dtbo_scenario_review_required=True)
    target=destination/'package.private.json';target.write_text(json.dumps(result,indent=2)+'\n')
    print('Offline image packaged twice identically; stock OS/security-patch word preserved. No boot test.')


if __name__=='__main__':main()
