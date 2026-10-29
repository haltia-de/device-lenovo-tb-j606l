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

No release exists yet. Do not publish a tag. Tags `v*.*.*` are protected.

## Writes

ADR 0102 (26 October 2026) replaces the old write rules. The agent may
boot, flash, switch slots, read and write over EDL and repartition the lab
unit without asking for each step. Three rules stay:

- The critical backup from 24 October is never overwritten. Read any other
  partition over EDL into `backups/` before writing it.
- Android on slot B stays a working way back. After every trial check
  `sys.boot_completed=1` on `_b`.
- Never write `modemst1`, `modemst2`, `fsg`, `fsc`, `persist` or the
  firmware partitions (`xbl*`, `tz*`, `rpm*`, `hyp*`, `abl*`, `devcfg*`).

`adb reboot edl` enters EDL; `qdl --storage=ufs` with the stock
`prog_firehose_ddr.elf` reads and writes partitions. The early Linux log
goes to the raw `logdump` partition (LUN 4) and is read back over EDL.
The J606F one-shot image from 23 October stays unused (ADR 0101).

## Layout

- `docs/dossier.md` is the hardware record from 23 October 2026.
- `docs/dual-boot.md`, `docs/reinstall.md` and `docs/camera.md` describe the
  working port: the dual boot, a clean install, the cameras.
- `docs/kernel-7.3.md` records the move to mainline 7.3, `docs/otg.md` the
  OTG trial, `docs/upstream.md` where the work can go upstream.
- `docs/adr/0100-follow-the-haltia-plan.md` binds this repository to the plan.
- `docs/adr/0101-oneshot-j606f-boot-retired.md` records the write word and
  retires the J606F one-shot boot. An ADR is a record. A later change is a
  new ADR.
- `docs/adr/0102-autonomous-device-work.md` replaces the write rules.
- `backups/` and `artifacts/` are git-ignored. Backups hold device-unique
  data. Do not commit them.

## Documented port status

The laboratory unit has Haltia installed alongside Android on slot B.
The Haltia kernel is in `recovery_b`, with its root in the separate
`haltia` partition; the active slot stays B. `docs/dual-boot.md` describes
the working port and known limitations. This is the documented laboratory
status, not a public release or a new hardware verification. The daily
bar remains display, touch, Wi-Fi, sound, sleep, the power button and
rotation. LTE, the camera, the pen, the pogo keyboard and the GPU come
after that bar.
