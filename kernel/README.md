# Kernel for the TB-J606L

Source: [TeamYogaBlade2/linux](https://github.com/TeamYogaBlade2/linux)
`blade/v7.1` at `7dd245445adf6eaa27018cf92fbd5a92ec0b118e` (Linux 7.1).

1. Copy `sm6115-lenovo-j606l.dts` to `arch/arm64/boot/dts/qcom/` and add
   `dtb-$(CONFIG_ARCH_QCOM) += sm6115-lenovo-j606l.dtb` to its Makefile.
2. Touch driver: take only the `drivers/input/touchscreen/nt36523/` files
   from `patches/0001-*.patch`
   (`git apply --include='drivers/input/touchscreen/nt36523/*'`), add
   `source "drivers/input/touchscreen/nt36523/Kconfig"` to the touchscreen
   Kconfig and `obj-$(CONFIG_TOUCHSCREEN_NT36523_SPI) += nt36523/` to its
   Makefile, then apply `patches/0002-*.patch`. Patch 0001 comes from
   hashtagbasit/SteamOS-ARM-Port (author guf296, GPL) for the NT36523N of
   the Lenovo TB321FU; 0002 adapts it to the J606L NT36523W through device tree properties:
   the event buffer at 0x2FE00, 12-bit coordinates in the screen's range,
   and the interrupt trigger from `interrupts`.
3. Backlight: `patches/0003-*.patch` adds `drivers/video/backlight/sgm37604a.c`
   (written for this port). Add its Kconfig entry next to the other
   backlight drivers:

   ```
   config BACKLIGHT_SGM37604A
   	tristate "SG Micro SGM37604A backlight"
   	depends on I2C
   ```
4. Config: arm64 `defconfig` plus `haltia-j606l.config`.
5. `make Image.gz modules qcom/sm6115-lenovo-j606l.dtb`, then
   `build-boot.sh <build dir> boot.img` and `fastboot flash recovery_b boot.img`.

The touch firmware (`novatek_ts_fw.bin`) is Lenovo's and stays out of the
repository: `haltia-firmware` copies it from the tablet's own `vendor_b` at
boot.
