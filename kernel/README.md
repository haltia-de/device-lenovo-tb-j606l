# Kernel for the TB-J606L

Source: [TeamYogaBlade2/linux](https://github.com/TeamYogaBlade2/linux)
`blade/v7.1` at `7dd245445adf6eaa27018cf92fbd5a92ec0b118e` (Linux 7.1), as
a plain copy of the tree.

```sh
kernel/build-kernel.sh <source tree> <work>     # Image.gz, modules, DTB
kernel/build-boot.sh <work>/build boot.img      # boot image for recovery_b
fastboot flash recovery_b boot.img
```

`build-kernel.sh` adds `sm6115-lenovo-j606l.dts`, applies the patches,
makes the config from arm64 `defconfig` plus `haltia-j606l.config`, and
packs the modules as `<work>/modules.tar` for `rootfs/build-rootfs.sh`
(`KERNEL_TAR`). It needs an aarch64 cross toolchain.

## Patches

- `0001` Novatek NT36523 SPI host-download touch driver, from
  hashtagbasit/SteamOS-ARM-Port (author guf296, GPL) for the NT36523N of
  the Lenovo TB321FU. Only its `drivers/input/touchscreen/nt36523/` files
  are used.
- `0002` adapts it to the J606L NT36523W through device tree properties:
  the event buffer at 0x2FE00, 12-bit coordinates in the screen's range,
  and the interrupt trigger from `interrupts`.
- `0003` brightness-only driver for the SGM37604A backlight (written for
  this port).
- `0004` makes `dwc3-qcom-legacy` set the UTMI pipe clock and the VBUS
  override again on resume; without it USB is gone after s2idle.
- `0005` hooks the touch driver into the touchscreen Kconfig and Makefile.
- `0006` driver for the four AW88258 speaker amplifiers (written for this
  port from Awinic's GPL aw882xx driver in Lenovo's sources). It loads each
  amplifier's register profile from the stock `awinic/aw882xx_acf.bin` and
  turns the profile's four-slot TDM frame into the two-slot I2S frame the
  LPASS primary MI2S port sends.
- `0007` secondary MI2S capture for the microphones: the DBMD8 voice
  processor drives the clocks (2 channels, 16 kHz, 32-bit slots), and the
  sm8250 machine driver makes `SECONDARY_MI2S_TX` a clock consumer. Also a
  small driver for the ES7210 ADC on the same port (Everest's Tab P11
  register sequences), the capture link's codec.
- `0008` double tap to wake. The panel keeps the NT36523W (a TDDI chip)
  powered and out of reset while the display sleeps
  (`novatek,tddi-touch-wake`). The touch driver puts its half into the
  gesture mode and reports the double tap as `KEY_WAKEUP`
  (`novatek,double-tap-wake`, sysfs `double_tap_wake`).

The touch firmware (`novatek_ts_fw.bin`) and the modem images are Lenovo's
and stay out of the repository: `rootfs/haltia-firmware` copies them from
the tablet's own `vendor_b` and `modem_b` at boot.
