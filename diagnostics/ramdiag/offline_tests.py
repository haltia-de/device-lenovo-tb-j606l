#!/usr/bin/env python3
"""Host fixtures and native C/PTY regression in the pinned image. No USB."""
import argparse
import os
from pathlib import Path
import re
import subprocess
import sys

HERE=Path(__file__).resolve().parent


def run(argv):subprocess.run(['rtk','proxy',*argv],check=True,timeout=120)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--image',required=True);p.add_argument('--work',type=Path,required=True)
    args=p.parse_args();out=args.work.resolve()
    if not re.fullmatch(r'sha256:[0-9a-f]{64}',args.image):p.error('Exact image ID required.')
    if out==HERE or out.is_relative_to(HERE):p.error('--work must be outside the source tree.')
    out.mkdir(mode=0o700,parents=True,exist_ok=True)
    run([sys.executable,'-B','-m','unittest','discover','-s',str(HERE),'-p','test_*.py','-v'])
    prefix=['docker','run','--rm','--pull=never','--network=none','--read-only','--cap-drop=ALL',
        '--security-opt=no-new-privileges','--user',f'{os.getuid()}:{os.getgid()}',
        '--pids-limit=64','--memory=1g','--tmpfs','/tmp:rw,nosuid,nodev,size=64m',
        '-v',f'{HERE}:/work:ro','-v',f'{out}:/out:rw',args.image]
    run([*prefix,'gcc','-Os','-Wall','-Wextra','-Werror','/work/test_diag_io.c','/work/diag_io.c','-lutil','-o','/out/test_diag_io'])
    run([*prefix,'/out/test_diag_io'])


if __name__=='__main__':main()
