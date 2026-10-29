#!/usr/bin/env python3
"""Read-only host observer library. A reviewed coordinator owns lock/recovery.

Running this file does not inspect USB. observe() is for a future separately
authorized single boot transaction; it issues no adb/fastboot/reboot commands.
"""
import fcntl
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import stat
import subprocess
import termios
import time
import tty

import proof

USB=Path('/sys/bus/usb/devices')
TTY=Path('/sys/class/tty')
DEV=Path('/dev')
LOCK=Path('/run/user/1000/haltia-tablet.lock')


def identity(port,usb=USB):
    p=usb/port
    try:
        return dict(vid=(p/'idVendor').read_text().strip(),pid=(p/'idProduct').read_text().strip(),
                    serial=(p/'serial').read_text().strip(),bus=(p/'busnum').read_text().strip(),
                    number=(p/'devnum').read_text().strip())
    except FileNotFoundError:
        return None


def candidates(port,usb=USB,ttys=TTY,dev=DEV):
    target=(usb/port).resolve(strict=True)
    found=[]
    for item in ttys.glob('ttyACM*'):
        if not re.fullmatch(r'ttyACM[0-9]+',item.name):continue
        try:
            physical=(item/'device').resolve(strict=True)
            if not physical.is_relative_to(target):continue
            major,minor=map(int,(item/'dev').read_text().strip().split(':'))
            node=dev/item.name
            st=node.stat()
            if stat.S_ISCHR(st.st_mode) and st.st_rdev==os.makedev(major,minor):found.append(node)
        except FileNotFoundError:
            continue
    return found



def validate_open_binding(fd,node,port,expected):
    # Revalidate after open, before any termios operation on the descriptor.
    if identity(port)!=expected or candidates(port)!=[node]:
        raise RuntimeError("ACM target changed during open.")
    opened=os.fstat(fd)
    current=node.stat(follow_symlinks=False)
    if (not stat.S_ISCHR(opened.st_mode) or not stat.S_ISCHR(current.st_mode)
            or opened.st_rdev!=current.st_rdev
            or identity(port)!=expected):
        raise RuntimeError("Opened ACM descriptor no longer matches the exact USB target.")


def unowned(node):
    result=subprocess.run(['rtk','proxy','fuser',str(node)],capture_output=True,timeout=5)
    if result.returncode!=1 or result.stdout.strip():
        raise RuntimeError('Target ACM node has an owner or ambiguous ownership.')
    if str(node).encode() in result.stderr and (b'Permission denied' in result.stderr or b'cannot stat' in result.stderr.lower()):
        raise RuntimeError('Cannot inspect the target ACM node.')


def observe(auth,manifest,output,lock):
    """Caller must retain lock until B is restored; this function never selects slots."""
    if os.fstat(lock.fileno()).st_ino!=LOCK.stat().st_ino:
        raise ValueError('Caller must supply the shared tablet-lock descriptor.')
    fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
    port=auth['usb_port']
    if not re.fullmatch(r'\d+-\d+(\.\d+)*',port):raise ValueError('Invalid exact USB port.')
    for key in ('fastboot_vid','fastboot_pid'):
        if not re.fullmatch(r'[0-9a-f]{4}',auth.get(key,'')):raise ValueError('Fresh fastboot VID/PID prerequisite missing.')
    if not auth.get('fastboot_serial'):raise ValueError('Fresh exact fastboot serial prerequisite missing.')
    output=Path(output)
    output.mkdir(mode=0o700)
    output.chmod(0o700)
    deadline=time.monotonic()+120
    capture=bytearray()
    selected=None
    initial=identity(port)
    initial_key=tuple(initial.values()) if initial else None
    departed=initial is None
    stream_closed=False
    fd=None
    oldattrs=None
    status=dict(proof_verified=False,bootloader_seen=False,needs_physical_fastboot=False,
                unexpected_reenumeration=False,android_b_restored=False)
    with (output/'usb-kernel-init.private.log').open('xb') as raw:
        os.chmod(raw.name,0o600)
        try:
            while time.monotonic()<deadline:
                ident=identity(port)
                if not ident or tuple(ident.values())!=initial_key:departed=True
                if departed and ident and ident['vid']==auth['fastboot_vid'] and ident['pid']==auth['fastboot_pid'] and ident['serial']==auth['fastboot_serial']:
                    status['bootloader_seen']=True
                    break
                if ident and ident['vid']=='1d6b' and ident['pid']=='0104' and ident['serial']==manifest['build_id']:
                    key=(ident['bus'],ident['number'])
                    if selected is not None and key!=selected:
                        status['unexpected_reenumeration']=True
                        break
                    if fd is None and not stream_closed:
                        nodes=candidates(port)
                        if len(nodes)>1:raise RuntimeError('Ambiguous target ACM binding.')
                        if nodes:
                            unowned(nodes[0])
                            if identity(port)!=ident:raise RuntimeError('USB binding changed before ACM open.')
                            fd=os.open(nodes[0],os.O_RDONLY|os.O_NONBLOCK|os.O_NOCTTY|os.O_CLOEXEC|os.O_NOFOLLOW)
                            validate_open_binding(fd,nodes[0],port,ident)
                            oldattrs=termios.tcgetattr(fd)
                            tty.setraw(fd,when=termios.TCSANOW)
                            selected=key
                    if fd is not None:
                        with selectors.DefaultSelector() as sel:
                            sel.register(fd,selectors.EVENT_READ)
                            if sel.select(min(0.25,max(0,deadline-time.monotonic()))):
                                try:data=os.read(fd,min(8192,proof.MAX_CAPTURE_BYTES-len(capture)))
                                except BlockingIOError:data=None
                                except OSError as error:
                                    if error.errno not in (errno.EIO,errno.ENODEV):raise
                                    data=b''
                                if data:
                                    raw.write(data);capture.extend(data)
                                    try:
                                        result=proof.verify(bytes(capture),manifest['build_id'],manifest['kernel_release'])
                                        status.update(result,proof_verified=True)
                                    except ValueError:pass
                                elif data==b'':
                                    if oldattrs is not None:
                                        try:termios.tcsetattr(fd,termios.TCSANOW,oldattrs)
                                        except (OSError,termios.error):pass
                                    os.close(fd);fd=None;oldattrs=None;stream_closed=True
                    elif stream_closed:
                        time.sleep(0.1)
                else:
                    time.sleep(0.1)
                if len(capture)>=proof.MAX_CAPTURE_BYTES:break
        finally:
            if fd is not None:
                if oldattrs is not None:
                    try:termios.tcsetattr(fd,termios.TCSANOW,oldattrs)
                    except (OSError,termios.error):pass
                os.close(fd)
    status['needs_physical_fastboot']=not status['bootloader_seen']
    status['capture_bytes']=len(capture)
    status['capture_sha256']=hashlib.sha256(capture).hexdigest()
    # Failure must be coordinated to fastboot/B by the caller, not a retry here.
    path=output/'usb-proof.sanitized.json'
    path.write_text(json.dumps(status,indent=2)+'\n');path.chmod(0o600)
    return status


if __name__=='__main__':
    print('Plan only. No USB inspected. A separately reviewed coordinator must supply the shared lock, fresh exact fastboot identity, root authorization and B recovery.')
