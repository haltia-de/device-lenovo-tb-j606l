#!/bin/sh
# Pack a TB-J606L boot image from a built kernel tree.
#   build-boot.sh <kernel build dir> <output.img>
# The DTB gets the overlay sink (dtb-overlay-sink.py), so ABL can apply the
# stock Lenovo DTBO and the image boots from recovery_b next to Android.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=$1
IMG=$2
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
python3 "$HERE/dtb-overlay-sink.py" "$OUT/scripts/dtc/dtc" \
	"$OUT/arch/arm64/boot/dts/qcom/sm6115-lenovo-j606l.dtb" \
	"$HERE/stock-dtbo-labels.txt" "$TMP/j606l.dtb"
# ABL wants a ramdisk. An empty one makes the kernel mount root= itself.
python3 -I - "$TMP/ramdisk.cpio.gz" <<'PY'
import gzip, sys
def entry(name, mode, ino):
    n = name.encode() + b'\0'
    h = b'070701' + b''.join(f'{x:08x}'.encode() for x in (ino, mode, 0, 0, 1, 0, 0, 0, 0, 0, 0, len(n), 0))
    d = h + n
    return d + b'\0' * (-len(d) % 4)
data = entry('.', 0o40755, 1) + entry('TRAILER!!!', 0, 2)
data += b'\0' * (-len(data) % 512)
open(sys.argv[1], 'wb').write(gzip.compress(data, 9, mtime=0))
PY
python3 -I "$HERE/mkbootimg.py" --kernel "$OUT/arch/arm64/boot/Image.gz" \
	--ramdisk "$TMP/ramdisk.cpio.gz" --dtb "$TMP/j606l.dtb" \
	--cmdline "root=PARTLABEL=haltia rootwait rw init=/sbin/haltia-init clk_ignore_unused pd_ignore_unused regulator_ignore_unused console=tty0 loglevel=4 log_buf_len=4M deferred_probe_timeout=60 cma=256M" \
	--header_version 2 --pagesize 4096 --base 0 --kernel_offset 0x8000 \
	--ramdisk_offset 0x1000000 --second_offset 0 --tags_offset 0x100 \
	--dtb_offset 0x1f00000 --os_version 11.0.0 --os_patch_level 2023-07 -o "$IMG"
sha256sum "$IMG"
