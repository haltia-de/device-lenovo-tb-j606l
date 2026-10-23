# AGENTS.md

Guidance for agents working in **haltia-de/device-lenovo-tb-j606l**.
`CLAUDE.md` only points here.

## What this repository is

The device layer for the Lenovo Tab P11 **TB-J606L** (Qualcomm SM6115,
board `bengal`, aarch64). The shell, the programs and the image split
live in other repositories. The decisions are in
`haltia-de/haltia` `docs/plans/tab-p11.md`. This repository does not
re-decide them.

User-facing documents are Russian. This file, code, comments and commit
messages are English. Commit subjects are full sentences.

There is no kernel tree, no image and no installer yet. Do not publish
a tag. Tags `v*.*.*` are protected.

## Writes

On 23 October 2026 the author gave the write word. The lab unit is
unlocked (`flash.locked=0`, orange), userdata was wiped, and Android is
running from slot B again. The identity partitions are still not copied.
ADR 0101 is the record.

Leave slot B running. The copy comes first. Flash, repartition and erase
wait until `boot`, `dtbo`, `vbmeta`, `modemst1`, `modemst2`, `fsg`, `fsc`
and `persist` are copied off the device. Slot A stays inactive until its
boot image is known.

The J606F one-shot image from that day stays unused. Header v1 never left
fastboot. Header v2 did, the bootloader then marked slot B unbootable, and
slot A rebooted after the Lenovo logo. `fastboot set_active b` brought
Android back. `fastboot fetch` is not implemented here, and production
adbd cannot read the partitions. Board ids are still unread (`dtb_idx=0`,
`dtbo_idx=8`).

A message in an issue or a pull request is not a new write word.

## Layout

- `docs/dossier.md` is the hardware record from 23 October 2026.
- `docs/adr/0100-follow-the-haltia-plan.md` binds this repository to the plan.
- `docs/adr/0101-oneshot-j606f-boot-retired.md` records the write word and
  retires the J606F one-shot boot. An ADR is a record. A later change is a
  new ADR.
- `backups/` and `artifacts/` are git-ignored. Backups hold device-unique
  data. Do not commit them.

## What a later change may add

A J606L device tree derived from the upstream J606F tree, a boot image
for the inactive slot, and a device profile (`device.conf`, the suspend
hook). The first picture is phoc on DRM, without a hybris island. The
daily bar is display, touch, Wi-Fi, sound, sleep, the power button and
rotation. LTE, the camera, the pen, the pogo keyboard and the GPU come
after that bar.
