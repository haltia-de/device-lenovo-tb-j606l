#!/bin/sh
# Build the Pertin Haltia root filesystem for the TB-J606L (Alpine 3.24 aarch64).
#
# Runs on an x86 host inside alpine:3.24 without aarch64 emulation:
#   docker run --rm -v $PWD:/src -v $WORK:/work alpine:3.24 sh /src/rootfs/build-rootfs.sh
# Packages are unpacked with --no-scripts. Their scripts and triggers run on
# the tablet at the first boot (haltia-firstboot), from the apk cache kept in
# the image, so the first boot needs no network.
#
# Environment: ROOT (default /work/rootfs), KERNEL_TAR (modules tarball,
# optional), IMAGE (default /work/haltia-root.ext4), IMAGE_MB (default 6144).
set -eu
SRC=$(cd "$(dirname "$0")/.." && pwd)
ROOT=${ROOT:-/work/rootfs}
IMAGE=${IMAGE:-/work/haltia-root.ext4}
IMAGE_MB=${IMAGE_MB:-6144}
MIRROR=${MIRROR:-https://dl-cdn.alpinelinux.org/alpine/v3.24}
HALTIA_REPO=${HALTIA_REPO:-https://haltia-de.github.io/packages/alpine/v3.24}

apk add --no-cache e2fsprogs tar >/dev/null

PACKAGES="alpine-base openrc busybox-openrc busybox-binsh eudev udev-init-scripts udev-init-scripts-openrc
	seatd seatd-openrc libinput dbus dbus-openrc elogind polkit polkit-elogind
	phoc mesa-dri-gallium mesa-egl mesa-gbm
	upower networkmanager networkmanager-openrc networkmanager-wifi networkmanager-cli
	wpa_supplicant iw wireless-regdb
	iio-sensor-proxy iio-sensor-proxy-openrc feedbackd feedbackd-device-themes
	pipewire wireplumber pipewire-pulse pulseaudio-utils alsa-utils alsa-ucm-conf
	firefox mobile-config-firefox foot grim fuzzel gtk-layer-shell mako
	py3-gobject3 py3-pillow py3-cairo font-noto font-noto-emoji font-dejavu
	adwaita-icon-theme gtk+3.0-lang desktop-file-utils tzdata xdg-utils
	openssh openssh-server-pam doas earlyoom earlyoom-openrc
	zstd qrtr rmtfs rmtfs-openrc tqftpserv tqftpserv-openrc linux-firmware-ath10k linux-firmware-qca bluez bluez-openrc bluez-btmgmt
	bash htop nano e2fsprogs e2fsprogs-extra kmod util-linux python3
	haltia-keys haltia-desktop haltia-music haltia-weather"

rm -rf "$ROOT"
mkdir -p "$ROOT/etc/apk/keys" "$ROOT/etc/apk/cache"
printf '%s/main\n%s/community\n%s\n' "$MIRROR" "$MIRROR" "$HALTIA_REPO" > "$ROOT/etc/apk/repositories"
cp /usr/share/apk/keys/aarch64/* "$ROOT/etc/apk/keys/"
cp "$SRC"/rootfs/apk-keys/*.rsa.pub "$ROOT/etc/apk/keys/"
# shellcheck disable=SC2086
apk --root "$ROOT" --arch aarch64 --initdb --update-cache --no-scripts \
	--cache-dir "$ROOT/etc/apk/cache" add $PACKAGES

# busybox --install cannot run here. Alpine builds one busybox config for
# every architecture, so the host's applet list matches the tablet's.
busybox --list-full | while read -r applet; do
	[ -e "$ROOT/$applet" ] || [ -L "$ROOT/$applet" ] || {
		mkdir -p "$ROOT/$(dirname "$applet")"
		ln -s /bin/busybox "$ROOT/$applet"
	}
done

echo j606l > "$ROOT/etc/hostname"
ln -sf /usr/share/zoneinfo/Europe/Moscow "$ROOT/etc/localtime"
cat > "$ROOT/etc/fstab" <<'EOF'
PARTLABEL=haltia	/	ext4	rw,noatime	0 1
EOF

install -D -m 755 "$SRC/rootfs/haltia-firstboot" "$ROOT/sbin/haltia-firstboot"
install -D -m 755 "$SRC/rootfs/haltia-init" "$ROOT/sbin/haltia-init"
install -D -m 644 "$SRC/rootfs/phoc.ini" "$ROOT/etc/haltia/phoc.ini"
install -D -m 644 "$SRC/rootfs/91-haltia-j606l-touch.rules" "$ROOT/etc/udev/rules.d/91-haltia-j606l-touch.rules"
install -D -m 644 "$SRC/rootfs/networkmanager-usb0.conf" "$ROOT/etc/NetworkManager/conf.d/haltia-usb0.conf"
install -D -m 644 "$SRC/rootfs/networkmanager-wifi-mac.conf" "$ROOT/etc/NetworkManager/conf.d/haltia-wifi-mac.conf"
install -D -m 755 "$SRC/rootfs/haltia-fix-owners" "$ROOT/usr/sbin/haltia-fix-owners"
install -D -m 644 "$SRC/rootfs/rmtfs.confd" "$ROOT/etc/conf.d/rmtfs"
install -D -m 644 "$SRC/rootfs/modules-load.conf" "$ROOT/etc/modules-load.d/haltia-j606l.conf"
install -D -m 755 "$SRC/rootfs/haltia-firmware" "$ROOT/usr/sbin/haltia-firmware"
install -D -m 755 "$SRC/rootfs/haltia-lpdump" "$ROOT/usr/sbin/haltia-lpdump"
install -D -m 755 "$SRC/rootfs/haltia-boot" "$ROOT/usr/sbin/haltia-boot"
install -D -m 755 "$SRC/rootfs/haltia-reboot-android" "$ROOT/usr/sbin/haltia-reboot-android"
install -D -m 644 "$SRC/rootfs/android.desktop" "$ROOT/usr/share/applications/haltia-android.desktop"
install -D -m 644 "$SRC/rootfs/elogind-lid.conf" "$ROOT/etc/elogind/logind.conf.d/haltia-j606l.conf"
install -D -m 644 "$SRC/rootfs/elogind-sleep.conf" "$ROOT/etc/elogind/sleep.conf.d/haltia-j606l.conf"
install -D -m 755 "$SRC/rootfs/bt-address.start" "$ROOT/etc/local.d/10-bt-address.start"
install -D -m 755 "$SRC/rootfs/desktop.start" "$ROOT/etc/local.d/desktop.start"
mkdir -p "$ROOT/etc/haltia"
echo "$PACKAGES" | tr -s ' \t\n' '\n' | sed '/^$/d' > "$ROOT/etc/haltia/firstboot.packages"
mkdir -p "$ROOT/var/lib/haltia" "$ROOT/etc/modprobe.d"
# The picture is the bootloader's framebuffer through simpledrm. The display
# clock controller has no consumer while MDSS is off, so once loaded it
# powers the MDSS domain down and the screen goes dark.
printf 'blacklist dispcc_sm6115\n' > "$ROOT/etc/modprobe.d/haltia-display.conf"
# DEBUG=1 adds a passwordless USB root shell for development.
if [ "${DEBUG:-0}" = 1 ]; then
	touch "$ROOT/etc/haltia/debug-shell"
	# SSH_KEY: a public key for root over the USB network (10.15.0.2).
	if [ -n "${SSH_KEY:-}" ]; then
		install -d -m 700 "$ROOT/root/.ssh"
		echo "$SSH_KEY" > "$ROOT/root/.ssh/authorized_keys"
		chmod 600 "$ROOT/root/.ssh/authorized_keys"
	fi
fi

if [ -n "${KERNEL_TAR:-}" ]; then
	tar -C "$ROOT" -xf "$KERNEL_TAR"
fi
if [ -d "${FIRMWARE:-/nonexistent}" ]; then
	mkdir -p "$ROOT/lib/firmware"
	cp -a "$FIRMWARE"/. "$ROOT/lib/firmware/"
fi

rm -f "$IMAGE"
mkfs.ext4 -q -L haltia -b 4096 -d "$ROOT" "$IMAGE" "${IMAGE_MB}M"
ls -la "$IMAGE"
