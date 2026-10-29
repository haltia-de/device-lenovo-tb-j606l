"""Offline state fixtures; no actual USB/tty node is inspected or opened."""
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
import os
import stat
import tempfile
import unittest
from unittest.mock import Mock, patch

import watch_usb as w

FB=dict(vid='18d1',pid='d00d',serial='fixture-private',bus='2',number='10')
ACM=dict(vid='1d6b',pid='0104',serial='haltia-j606l-0123456789abcdef',bus='2',number='11')
AUTH=dict(usb_port='2-1.4',fastboot_vid=FB['vid'],fastboot_pid=FB['pid'],fastboot_serial=FB['serial'])
MANIFEST=dict(build_id=ACM['serial'],kernel_release='fixture')


class WatchTests(unittest.TestCase):
    def observe_fixture(self,states,acm=False):
        current=[states[0]]
        remaining=iter(states)
        def identity(_):
            current[0]=next(remaining,current[0]);return current[0]
        tick=[0]
        def clock():tick[0]+=1;return tick[0]
        with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            root=Path(tmp);lockpath=root/'lock';lockpath.touch()
            stack.enter_context(patch.object(w,'LOCK',lockpath))
            stack.enter_context(patch.object(w,'identity',side_effect=identity))
            stack.enter_context(patch.object(w.time,'monotonic',side_effect=clock))
            stack.enter_context(patch.object(w.time,'sleep'))
            stack.enter_context(patch.object(w,'candidates',return_value=[Path('/fixture/ttyACM0')]))
            stack.enter_context(patch.object(w,'unowned'))
            # Only ACM fixture reaches open; lock/output files use normal Python IO.
            opened=stack.enter_context(patch.object(w.os,'open',return_value=123))
            closed=stack.enter_context(patch.object(w.os,'close'))
            stack.enter_context(patch.object(w,'validate_open_binding'))
            stack.enter_context(patch.object(w.termios,'tcgetattr',return_value=[]))
            stack.enter_context(patch.object(w.termios,'tcsetattr'))
            stack.enter_context(patch.object(w.tty,'setraw'))
            selector=Mock();selector.__enter__=Mock(return_value=selector);selector.__exit__=Mock(return_value=False)
            selector.select.return_value=[(None,None)]
            stack.enter_context(patch.object(w.selectors,'DefaultSelector',return_value=selector))
            stack.enter_context(patch.object(w.os,'read',return_value=b''))
            with lockpath.open('rb') as lock:
                result=w.observe(AUTH,MANIFEST,root/'out',lock)
            return result,opened.call_count,closed.call_count

    def test_initial_fastboot_is_not_a_return(self):
        result,opened,_=self.observe_fixture([FB,FB])
        self.assertFalse(result['bootloader_seen'])
        self.assertTrue(result['needs_physical_fastboot'])
        self.assertEqual(opened,0)

    def test_observed_departure_then_fresh_fastboot_is_return(self):
        result,_,_=self.observe_fixture([FB,FB,None,dict(FB,number='12')])
        self.assertTrue(result['bootloader_seen'])

    def test_acm_eof_closes_then_waits_for_fastboot(self):
        result,opened,closed=self.observe_fixture([FB,None,ACM,ACM,None,dict(FB,number='12')],True)
        self.assertTrue(result['bootloader_seen'])
        self.assertFalse(result['needs_physical_fastboot'])
        self.assertEqual((opened,closed),(1,1))

    def test_postopen_binding_rejects_hotplug_before_termios(self):
        node=Path('/fixture/ttyACM0')
        ch=SimpleNamespace(st_mode=stat.S_IFCHR,st_rdev=os.makedev(166,0))
        other=SimpleNamespace(st_mode=stat.S_IFCHR,st_rdev=os.makedev(166,1))
        with patch.object(w,'identity',return_value=ACM),patch.object(w,'candidates',return_value=[node]),patch.object(w.os,'fstat',return_value=ch),patch.object(Path,'stat',return_value=ch):
            w.validate_open_binding(123,node,AUTH['usb_port'],ACM)
            with patch.object(w.os,'fstat',return_value=other),self.assertRaises(RuntimeError):
                w.validate_open_binding(123,node,AUTH['usb_port'],ACM)
            with patch.object(w,'candidates',return_value=[]),self.assertRaises(RuntimeError):
                w.validate_open_binding(123,node,AUTH['usb_port'],ACM)
            with patch.object(w,'identity',return_value=dict(ACM,number='99')),self.assertRaises(RuntimeError):
                w.validate_open_binding(123,node,AUTH['usb_port'],ACM)


if __name__=='__main__':unittest.main()
