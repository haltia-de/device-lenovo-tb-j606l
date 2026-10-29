# Kernel for the TB-J606L

Source: mainline Linux 7.3 from kernel.org,
[`linux-7.3.tar.xz`](https://cdn.kernel.org/pub/linux/kernel/v7.x/linux-7.3.tar.xz)
(sha256 `87363c24f10e06321eb362765521094e94471f6bff8bce2d6b3e40f39f004953`),
unpacked. Until 28 October 2026 the port built TeamYogaBlade2/linux
`blade/v7.1`, which matches Linux 7.1 for the SM6115.

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
- `0010` an SM6115 CAMSS: the QCM2290 CSIDs and TFEs plus a third CSIPHY,
  which the front camera uses.
- `0011` the OV8856 driver keeps the Bayer order set_format chose;
  get_format and open() reset it, and libcamera's stream failed with EPIPE.
- `0012` the CAMSS CSIPHY settle count waits the middle of the D-PHY
  window instead of its minimum; at 180 MHz every packet had CRC errors.
  See `docs/camera.md`.
- `0013` the SMP2P sleep state driver from downstream: bit 12 of the
  ADSP's "sleepstate" entry tells its sensor framework whether the system
  is awake, and its "sleepstate_see" bit wakes the system.
- `0014` the NT36523 panel removes itself from the panel list when its DSI
  attach fails; it was freed while still listed, and the touch driver
  following it oopsed (issue #24).
- `0015` fastrpc takes a hard wakeup event for every message from the DSP,
  so a system in s2idle wakes and user space can answer.
- `0016` fastrpc resumes an invocation a signal interrupted instead of
  sending it again. The freezer interrupts hexagonrpcd's listener on every
  suspend; the duplicate crashed the ADSP sensor process at resume
  (issue #23). See `docs/sleep.md`.
- `0017` psci-cpuidle initializes at late_initcall_sync. Its faux device
  probes once, and with the MPM as the CPU clusters' parent the PSCI
  domains come only from the deferred probes; cpuidle failed and the CPUs
  only ran WFI. 7.3 still probes psci-cpuidle once.
- `0018` the touch driver's ESD check workqueue says WQ_PERCPU; 7.3 warns
  about a workqueue that sets neither WQ_PERCPU nor WQ_UNBOUND.
- `0019` the WCD937x SoundWire devices add their components from a work
  item. The codec's probe waits for the TX device, which the bus cannot
  initialise while the TX device's own probe holds its lock; when TX came
  last the sound card failed after 5 s.

- `0020` QRTR keeps the HELLO handshake of 7.2: packets to a node are sent
  before the core's HELLO went out, and the name service answers every
  remote HELLO. With the 7.3 handshake the modem often stalled at boot (2
  of 42 services, its watchdog fired after 40 s) and Wi-Fi came up late
  (issue #31).

The SM6115 eGPIO function (formerly `0009`) is in mainline since 7.2.

The touch firmware (`novatek_ts_fw.bin`) and the modem images are Lenovo's
and stay out of the repository: `rootfs/haltia-firmware` copies them from
the tablet's own `vendor_b` and `modem_b` at boot.
