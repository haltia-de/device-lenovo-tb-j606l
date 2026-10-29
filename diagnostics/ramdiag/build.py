#!/usr/bin/env python3
"""Offline-only reproducible staging/build. Contains no device commands."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import struct
import tarfile

HERE = Path(__file__).resolve().parent
CACHE = None
WORK = None
PIN = '7dd245445adf6eaa27018cf92fbd5a92ec0b118e'
UPSTREAM = '7a78f7ba9f24962c8033e0152bf34a7903ff61ba'
BUILD_ID_TOOLCHAIN_SEED = 'sha256:32e11b67e8d63a43ba674de8f1725f809d02649e183ad68a2e3c9e5e2ba44115'
IMAGE = None
BASE_DTS_SHA = '8664cb3e3d74011fbd20cd55df69266e06ddb44d2e0daa037fae8881881f428e'
COMPARISON = HERE/'source-comparison.json'
TARGET = 'sm6115-lenovo-j606l-ramdiag'
FORBIDDEN = ('BLOCK','DRM','FB','SCSI','MMC','MTD','ATA','NVME_CORE','MODULES','REMOTEPROC',
             'USB_CONFIGFS_MASS_STORAGE','USB_CONFIGFS_F_FS','USB_G_SERIAL')
REQUIRED = ('ARM64','ARCH_QCOM','BLK_DEV_INITRD','DEVTMPFS','PROC_FS','SYSFS','CONFIGFS_FS',
            'USB_GADGET','USB_DWC3','USB_DWC3_GADGET','USB_DWC3_QCOM','USB_CONFIGFS','USB_CONFIGFS_ACM',
            'PHY_QCOM_QUSB2','SM_GCC_6115','QCOM_SMD_RPM','RPMSG_QCOM_GLINK_RPM',
            'REGULATOR_QCOM_SMD_RPM','PINCTRL_SM6115','SPMI_MSM_PMIC_ARB','INTERCONNECT_QCOM_SM6115',
            'POWER_RESET_MSM','POWER_RESET_QCOM_PON','REBOOT_MODE')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for part in iter(lambda: stream.read(1024*1024),b''): h.update(part)
    return h.hexdigest()


def run(argv,timeout=60,log=None):
    result = subprocess.run(['rtk','proxy',*argv],capture_output=True,text=True,timeout=timeout)
    if log:
        Path(log).write_text(result.stdout+result.stderr)
        Path(log).chmod(0o600)
    if result.returncode:
        raise RuntimeError('Offline command failed; inspect private build log.')
    return result.stdout


def save(name,value):
    (WORK/name).write_text(json.dumps(value,indent=2)+'\n')
    (WORK/name).chmod(0o600)


def stage():
    if run(['git','-C',str(CACHE),'rev-parse','HEAD']).strip() != PIN or run(['git','-C',str(CACHE),'status','--porcelain']).strip():
        raise ValueError('Cached source pin/clean tree differs.')
    original = CACHE/'arch/arm64/boot/dts/qcom/sm6115p-lenovo-j606f.dts'
    if sha(original) != BASE_DTS_SHA:
        raise ValueError('Compared J606F baseline differs.')
    if shutil.disk_usage(WORK).free < 12*1024**3:
        raise ValueError('Need 12 GiB free for isolated source/build.')
    source = WORK/'linux-src'
    stamp = WORK/'stage.private.json'
    if not source.exists():
        source.mkdir(mode=0o700)
        with (WORK/'archive.private.log').open('wb') as log:
            proc = subprocess.Popen(['rtk','proxy','git','-C',str(CACHE),'archive','--format=tar',PIN],stdout=subprocess.PIPE,stderr=log)
            try:
                with tarfile.open(fileobj=proc.stdout,mode='r|') as archive:
                    archive.extractall(source,filter='data')
                if proc.wait(timeout=30): raise RuntimeError('Pinned source archive failed.')
            finally:
                if proc.poll() is None: proc.kill();proc.wait(timeout=5)
    elif not stamp.exists() or json.loads(stamp.read_text())['source_pin'] != PIN:
        raise ValueError('Unrecognized partial staging directory; inspect before reuse.')
    if (source/'.git').exists(): raise ValueError('Source must be a plain copy without .git.')
    qcom = source/'arch/arm64/boot/dts/qcom'
    shutil.copyfile(HERE/(TARGET+'.dts'),qcom/(TARGET+'.dts'))
    makefile = qcom/'Makefile'
    text = makefile.read_text()
    line = f'dtb-$(CONFIG_ARCH_QCOM) += {TARGET}.dtb\n'
    if line not in text: makefile.write_text(text+'\n'+line)
    save('stage.private.json',dict(source_pin=PIN,earlier_official_dts_pin=UPSTREAM,
        baseline_dts_sha256=BASE_DTS_SHA,source_comparison_sha256=sha(COMPARISON),plain_copy_without_git=True,
        profile_dts_sha256=sha(HERE/(TARGET+'.dts')),staged_makefile_sha256=sha(makefile)))
    return source


def container(out):
    owner = out.stat()
    return ['docker','run','--rm','--pull=never','--network=none','--read-only','--cap-drop=ALL',
        '--security-opt=no-new-privileges','--pids-limit=256','--memory=8g','--cpus=4',
        '--user',f'{owner.st_uid}:{owner.st_gid}','--tmpfs','/tmp:rw,nosuid,nodev,size=512m',
        '-e','SOURCE_DATE_EPOCH=1792800000','-v',f'{HERE}:/work:ro',
        '-v',f'{WORK/"linux-src"}:/src:ro','-v',f'{out}:/out:rw',IMAGE]


def check_config(path):
    values = {}
    for line in path.read_text().splitlines():
        if line.startswith('CONFIG_') and '=' in line:
            name,value = line[7:].split('=',1);values[name]=value
    missing = [name for name in REQUIRED if values.get(name) != 'y']
    unsafe = [name for name in FORBIDDEN if values.get(name) not in (None,'n')]
    if missing or unsafe:
        save('config-rejection.private.json',dict(missing=missing,unsafe=unsafe))
        raise ValueError('Required/safety kernel configuration differs; inspect config-rejection.private.json.')
    if values.get('INITRAMFS_SOURCE') != '""' or values.get('CMDLINE') != '"rdinit=/init panic=0 loglevel=7"' or values.get('CMDLINE_FORCE') != 'y':
        raise ValueError('External private initramfs/cmdline configuration differs.')
    return values


def check_init_elf(path):
    data = path.read_bytes()
    if len(data) < 64 or data[:6] != b'\x7fELF\x02\x01' or struct.unpack_from('<HH',data,16) != (2,183):
        raise ValueError('PID1 must be a new static AArch64 ELF64 executable.')
    offset = struct.unpack_from('<Q',data,32)[0]
    stride,count = struct.unpack_from('<HH',data,54)
    if stride != 56 or offset+stride*count > len(data):
        raise ValueError('PID1 ELF program headers invalid.')
    types = [struct.unpack_from('<I',data,offset+i*stride)[0] for i in range(count)]
    if 2 in types or 3 in types:
        raise ValueError('PID1 must not have PT_DYNAMIC or PT_INTERP.')
    return dict(machine='AArch64',elf_class=64,type='EXEC',static_no_dynamic_or_interpreter=True)


def main():
    global CACHE, WORK, IMAGE
    os.umask(0o077)
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage-only',action='store_true')
    p.add_argument('--build',action='store_true')
    p.add_argument('--source',type=Path)
    p.add_argument('--work',type=Path)
    p.add_argument('--image',help='Exact sha256 Docker image ID built from Dockerfile.toolchain.')
    args = p.parse_args()
    if not args.stage_only and not args.build:
        print('Offline plan only. New plain source copy, fresh no-block/no-MDSS kernel and new PID1. No tablet operations.')
        return
    if args.source is None or args.work is None:
        p.error('--source and --work are required; generated files stay outside the publishable tree.')
    CACHE=args.source.resolve();WORK=args.work.resolve();IMAGE=args.image
    if WORK==HERE or WORK.is_relative_to(HERE):
        p.error('--work must be outside the publishable source tree.')
    if args.build and (not IMAGE or not __import__('re').fullmatch(r'sha256:[0-9a-f]{64}',IMAGE)):
        p.error('--build requires --image sha256:<exact image ID>.')
    WORK.mkdir(mode=0o700,parents=True,exist_ok=True)
    stage()
    if not args.build:
        print('Pinned plain source staged; no kernel or device executed.')
        return
    out = WORK/'build'
    out.mkdir(mode=0o700,exist_ok=True)
    prefix = container(out)
    packages = run([*prefix,'cat','/j606l-toolchain-packages.tsv'])
    installed = run([*prefix,'dpkg-query','-W','-f=${binary:Package}\t${Version}\n'])
    if installed != (HERE/'toolchain-packages.lock.tsv').read_text():
        raise ValueError('Reconstructed toolchain package inventory differs from lock.')
    (WORK/'toolchain-packages.tsv').write_text(packages)
    (WORK/'toolchain-packages.tsv').chmod(0o600)
    base = ['make','-C','/src','O=/out','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-',
            'KBUILD_BUILD_USER=haltia','KBUILD_BUILD_HOST=reproducible','KBUILD_BUILD_VERSION=1',
            'KBUILD_BUILD_TIMESTAMP=Sat Oct 24 00:00:00 UTC 2026','KCFLAGS=-ffile-prefix-map=/src=linux-src -ffile-prefix-map=/out=build']
    run([*prefix,*base,'KCONFIG_ALLCONFIG=/work/ramdiag.config','allnoconfig'],180,WORK/'configure.private.log')
    check_config(out/'.config')
    inputs = {name:sha(HERE/name) for name in ('init.c','diag_io.c','diag_io.h','ramdiag.config',TARGET+'.dts')}
    build_id = 'haltia-j606l-'+hashlib.sha256((PIN+json.dumps(inputs,sort_keys=True)+sha(out/'.config')+BUILD_ID_TOOLCHAIN_SEED).encode()).hexdigest()[:16]
    userspace = out/'ramdiag-userspace'
    userspace.mkdir(mode=0o700,exist_ok=True)
    run([*prefix,'aarch64-linux-gnu-gcc','-static','-Os','-s','-Wall','-Wextra','-Werror',
        '-ffile-prefix-map=/work=.',f'-DDIAG_BUILD_ID="{build_id}"','/work/init.c','/work/diag_io.c','-o','/out/ramdiag-userspace/init'],60,WORK/'init-compile.private.log')
    elf = check_init_elf(userspace/'init')
    run([*prefix,*base,'-j4','Image.gz',f'qcom/{TARGET}.dtb'],1800,WORK/'kernel-build.private.log')
    check_config(out/'.config')
    if any(sha(HERE/name)!=value for name,value in inputs.items()):
        raise ValueError('Build inputs changed during compilation; no provenance claim written.')
    save('kernel-build.private.json',dict(kernel_source_pin=PIN,toolchain_image=IMAGE,build_id_toolchain_seed=BUILD_ID_TOOLCHAIN_SEED,build_id=build_id,
        config_sha256=sha(out/'.config'),init_source_sha256=sha(HERE/'init.c'),init_binary_sha256=sha(userspace/'init'),
        input_hashes=inputs,init_binary_path=str(userspace/'init'),
        init_elf=elf,toolchain_package_versions=dict(line.split('\t',1) for line in packages.splitlines()),
        image_gz_sha256=sha(out/'arch/arm64/boot/Image.gz'),dtb_sha256=sha(out/f'arch/arm64/boot/dts/qcom/{TARGET}.dtb'),
        no_device_commands=True,no_boot_test=True))
    print('Offline kernel/init build complete; no device or diagnostic image executed.')


if __name__ == '__main__':
    main()
