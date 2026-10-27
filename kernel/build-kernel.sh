#!/bin/sh
# Build the TB-J606L kernel from a clean source tree.
#   build-kernel.sh <pinned source tree> <work dir>
# The source is TeamYogaBlade2/linux blade/v7.1 at the commit in README.md,
# as a plain copy. Needs an aarch64 cross toolchain (CROSS_COMPILE, default
# aarch64-linux-gnu-). Leaves <work>/build (the build tree, for
# build-boot.sh) and <work>/modules.tar (for rootfs/build-rootfs.sh).
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
SRC=$1
WORK=$2
CROSS_COMPILE=${CROSS_COMPILE:-aarch64-linux-gnu-}
JOBS=${JOBS:-$(nproc)}
K=$WORK/linux
OUT=$WORK/build

mkdir -p "$WORK"
rm -rf "$K"
cp -a "$SRC" "$K"

# Device tree.
cp "$HERE/sm6115-lenovo-j606l.dts" "$K/arch/arm64/boot/dts/qcom/"
echo 'dtb-$(CONFIG_ARCH_QCOM)	+= sm6115-lenovo-j606l.dtb' >> "$K/arch/arm64/boot/dts/qcom/Makefile"

# Touch driver: only its own directory from the imported patch.
(cd "$K" && git apply --include='drivers/input/touchscreen/nt36523/*' \
	"$HERE/patches/0001-input-touchscreen-add-novatek-nt36523-spi.patch")
for p in "$HERE"/patches/[0-9][0-9][0-9][0-9]-*.patch; do
	case $p in */0001-*) continue ;; esac
	patch -d "$K" -p1 -s < "$p"
done

# Config: arm64 defconfig plus the device fragment.
cp "$K/arch/arm64/configs/defconfig" "$K/arch/arm64/configs/haltia_j606l_defconfig"
cat "$HERE/haltia-j606l.config" >> "$K/arch/arm64/configs/haltia_j606l_defconfig"
make -s -C "$K" O="$OUT" ARCH=arm64 CROSS_COMPILE="$CROSS_COMPILE" haltia_j606l_defconfig
for c in $(grep -o '^CONFIG_[A-Z0-9_]*=[ym]' "$HERE/haltia-j606l.config"); do
	grep -qx "$c" "$OUT/.config" || { echo "config: $c did not stick" >&2; exit 1; }
done

make -s -C "$K" O="$OUT" ARCH=arm64 CROSS_COMPILE="$CROSS_COMPILE" -j"$JOBS" \
	Image.gz modules qcom/sm6115-lenovo-j606l.dtb
rm -rf "$WORK/modroot"
make -s -C "$K" O="$OUT" ARCH=arm64 CROSS_COMPILE="$CROSS_COMPILE" \
	INSTALL_MOD_PATH="$WORK/modroot" INSTALL_MOD_STRIP=1 modules_install
tar -C "$WORK/modroot" -cf "$WORK/modules.tar" lib
echo "kernel $(cat "$OUT/include/config/kernel.release")"
