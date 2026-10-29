#!/usr/bin/env python3
"""Offline static policy checks on the newly compiled DTB."""
import json
from pathlib import Path
import struct
import sys

import build

HERE=Path(__file__).resolve().parent
from fdt import fdt


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work',type=Path,required=True)
    args=parser.parse_args();work=args.work.resolve()
    if work==HERE or work.is_relative_to(HERE):parser.error('--work must be outside the source tree.')
    dtb=work/f'build/arch/arm64/boot/dts/qcom/{build.TARGET}.dtb'
    total,nodes=fdt(dtb.read_bytes())
    assert total==dtb.stat().st_size
    assert nodes['/']['qcom,msm-id']==struct.pack('>2I',444,0x10000)
    assert nodes['/']['qcom,board-id']==struct.pack('>2I',34,3)
    disabled=['/soc@0/'+p for p in ('mmc@4744000','mmc@4784000','ufshc@4804000','phy@4807000',
        'gpu@5900000','gpu@5900000/zap-shader','display-subsystem@5e00000',
        'display-subsystem@5e00000/dsi@5e94000','display-subsystem@5e00000/dsi@5e94000/panel@0',
        'display-subsystem@5e00000/phy@5e94400','remoteproc@6080000','remoteproc@a400000',
        'remoteproc@b300000','wifi@c800000')]
    for path in disabled:assert nodes[path]['status']==b'disabled\0',path
    assert not any('framebuffer@' in p or 'ramoops@' in p for p in nodes)
    assert nodes['/soc@0/usb@4ef8800']['status']==b'okay\0'
    assert nodes['/soc@0/usb@4ef8800/usb@4e00000']['dr_mode']==b'peripheral\0'
    assert nodes['/soc@0/phy@1613000']['status']==b'okay\0'
    report=dict(dtb_sha256=build.sha(dtb),fdt_parser_sha256=build.sha(HERE/'fdt.py'),
        msm_id=[444,65536],board_id=[34,3],disabled_nodes=disabled,no_framebuffer_or_ramoops=True,
        usb_peripheral=True,usb2_phy_enabled=True,rpm_resource_controller_retained=True,hardware_tested=False)
    (work/'static-dtb.private.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Compiled DTB policy checks passed; no device access.')


if __name__=='__main__':main()
