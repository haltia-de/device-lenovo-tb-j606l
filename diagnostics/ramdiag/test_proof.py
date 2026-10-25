import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
import zlib

import proof
import watch_usb

BUILD='haltia-j606l-0123456789abcdef'
RELEASE='7.1.0-haltia-j606l-ramdiag-01'


def frame(log=None):
    if log is None:log=b'6,0,1,-;Linux version '+RELEASE.encode()+b'\nembedded LF\nCR\rNUL\x00end\n'
    base=(f'HALTIA_J606L_KERNEL build={BUILD} sysname=Linux release={RELEASE} machine=aarch64\n'
          f'HALTIA_J606L_INIT build={BUILD} pid=1 rootfs_magic=0x858458f6 model=Lenovo Tab P11 TB-J606L RAM diagnostic\n'
          'HALTIA_J606L_POLICY block_support=disabled mdss=disabled persistent_mounts=none\n').encode()
    header=f'HALTIA_J606L_KMSG_BEGIN build={BUILD} bytes={len(log)} crc32={zlib.crc32(log):08x} flags=0\n'.encode()
    end=f'\nHALTIA_J606L_KMSG_END build={BUILD} bytes={len(log)}\n'.encode()
    return base+header+log+end


class ProofTests(unittest.TestCase):
    def test_kernel_init_and_byte_exact_early_log_are_required(self):
        result=proof.verify(frame(),BUILD,RELEASE)
        self.assertTrue(result['early_kernel_log_crc_valid'])
        self.assertTrue(result['pid1_proof'])

    def test_late_attach_accepts_later_complete_repeated_frame(self):
        raw=frame()
        self.assertTrue(proof.verify(raw[len(raw)//2:]+raw,BUILD,RELEASE)['early_kernel_log_crc_valid'])

    def test_three_proof_lines_without_log_are_insufficient(self):
        raw=frame().split(b'HALTIA_J606L_KMSG_BEGIN',1)[0]
        with self.assertRaises(ValueError):proof.verify(raw,BUILD,RELEASE)

    def test_cooked_newlines_corruption_and_incomplete_frames_rejected(self):
        raw=frame()
        for bad in (raw.replace(b'\n',b'\r\n'),raw[:-5],raw.replace(b'embedded',b'corrupted'),raw.replace(b'machine=aarch64',b'machine=x86_64')):
            with self.subTest(length=len(bad)),self.assertRaises(ValueError):proof.verify(bad,BUILD,RELEASE)

    def test_wrong_build_pid_and_nonram_root_rejected(self):
        for bad in (frame().replace(BUILD.encode(),b'haltia-j606l-fedcba9876543210'),frame().replace(b'pid=1 ',b'pid=2 '),frame().replace(b'0x858458f6',b'0xef53')):
            with self.assertRaises(ValueError):proof.verify(bad,BUILD,RELEASE)

    def test_log_bounds_and_missing_early_kernel_version_rejected(self):
        for raw in (frame(b'x'*(proof.MAX_LOG_BYTES+1)),frame(b'no early kernel here'),b'x'*(proof.MAX_CAPTURE_BYTES+1)):
            with self.assertRaises(ValueError):proof.verify(raw,BUILD,RELEASE)

    def test_exact_usb_identity_and_tty_ancestry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);usb=root/'usb';ttys=root/'tty';dev=root/'dev'
            for p in (usb/'2-1.4',usb/'2-1.5',ttys/'ttyACM0',dev):p.mkdir(parents=True,exist_ok=True)
            target=usb/'2-1.4'
            for name,value in dict(idVendor='1d6b',idProduct='0104',serial=BUILD,busnum='2',devnum='3').items():(target/name).write_text(value)
            (ttys/'ttyACM0'/'device').symlink_to(usb/'2-1.5')
            (ttys/'ttyACM0'/'dev').write_text('166:0')
            self.assertEqual(watch_usb.identity('2-1.4',usb)['serial'],BUILD)
            self.assertEqual(watch_usb.candidates('2-1.4',usb,ttys,dev),[])
            (ttys/'ttyACM0'/'device').unlink();(ttys/'ttyACM0'/'device').symlink_to(target)
            # No actual device open: this stat result models only /dev/ttyACM0.
            original=Path.stat
            def node_stat(path,*args,**kwargs):
                if path==dev/'ttyACM0':
                    class Node:st_mode=stat.S_IFCHR|0o660;st_rdev=os.makedev(166,0)
                    return Node()
                return original(path,*args,**kwargs)
            with patch.object(Path,'stat',node_stat):
                self.assertEqual(watch_usb.candidates('2-1.4',usb,ttys,dev),[dev/'ttyACM0'])


if __name__=='__main__':unittest.main()
