# Чистая установка Linux на TB-J606L

Порядок, по которому образ собирали и ставили 27 октября 2026 (#20 и
установка с камерой). Пути — с машины разработчика, их можно менять.
Правила записи — ADR 0102: перед записью раздел читается в `backups/`,
Android на `_b` после каждой пробы должен давать `sys.boot_completed=1`.

## 1. Ядро

Источник — Linux 7.3 с kernel.org, архив и его sha256 указаны в
`kernel/README.md`, распакованный без изменений:

```
S=/mnt/data/tmp/mainline/linux-7.3 W=/mnt/data/tmp/mainline/j606l-7.3
curl -LO https://cdn.kernel.org/pub/linux/kernel/v7.x/linux-7.3.tar.xz
echo '87363c24f10e06321eb362765521094e94471f6bff8bce2d6b3e40f39f004953  linux-7.3.tar.xz' | sha256sum -c
tar -xJf linux-7.3.tar.xz -C /mnt/data/tmp/mainline
docker run --rm -u $(id -u):$(id -g) -v $PWD:/repo:ro -v $S:/src:ro -v $W:/work \
	haltia-j606l-kbuild:1 sh -c 'JOBS=6 /repo/kernel/build-kernel.sh /src /work'
kernel/build-boot.sh $W/build $W/haltia-boot.img
```

`build-kernel.sh` применяет все `kernel/patches/NNNN-*.patch` (0001 — только
каталог драйвера тача) и проверяет, что каждая строка
`haltia-j606l.config` попала в `.config`. С 6 потоками сборка идёт около
часа. На выходе `$W/build` и `$W/modules.tar`.

## 2. Оверлей оболочки

Пока доработки оболочки не вышли пакетом, их файлы кладутся оверлеем поверх
выпуска. 27 октября это четыре файла с ветки `double-tap-wake` (PR #79 и
#81 в `haltia-de/shell`):

```
O=$W/overlay
git -C shell show origin/double-tap-wake:bin/haltia-rotate > $O/usr/bin/haltia-rotate
git -C shell show origin/double-tap-wake:libexec/haltia-sleep > $O/usr/libexec/haltia/haltia-sleep
git -C shell show origin/double-tap-wake:libexec/haltia-volume > $O/usr/libexec/haltia/haltia-volume
git -C shell show origin/double-tap-wake:etc/udev-haltia-panel.rules > $O/usr/lib/udev/rules.d/90-haltia-panel.rules
```

Права: 755 для программ, 644 для правила. Когда выпуск оболочки их
содержит, оверлей не нужен.

## 3. Корень

```
docker run --rm -v $PWD:/src:ro -v $W:/work -e DEBUG=1 \
	-e "SSH_KEY=$(cat ~/.ssh/id_ed25519.pub)" -e KERNEL_TAR=/work/modules.tar \
	-e OVERLAY=/work/overlay alpine:3.24 sh /src/rootfs/build-rootfs.sh
```

Пакеты берутся свежими из Alpine и `haltia-de.github.io/packages`. Образ —
`$W/haltia-root.ext4`, 6 ГиБ, на первой загрузке растягивается на раздел
(37,7 ГиБ). `DEBUG=1` с ключом даёт root по SSH на `10.15.0.2` (USB) для
разработки.

## 4. Резервные копии и запись

Перед записью: корень с планшета по SSH (`tar --one-file-system | zstd`) и
`recovery_b` по EDL — в `backups/<дата>-.../`. Вход в EDL — из Android
(`adb reboot edl`). `qdl` запускать сразу, иначе он зависает:

```
Q=/mnt/data/tmp/haltia-qdl-hostcheck/qdl
P=/mnt/data/tmp/haltia-j606l-research/S320435/prog_firehose_ddr.elf
N=$(( $(stat -c %s $W/haltia-boot.img) / 4096 ))
$Q --backend=usb --storage=ufs $P \
	read 0/88840+24576 recovery_b-before.bin \
	write 0/88840 $W/haltia-boot.img \
	write 0/20040488 $W/haltia-root.ext4 \
	read 0/88840+$N recovery_b-after.bin
cmp recovery_b-after.bin $W/haltia-boot.img
```

LUN 0: `recovery_b` с сектора 88840 (24576 секторов по 4 КиБ), раздел
`haltia` с 20040488. Запись 6 ГиБ — около 5 минут.

`qdl reset` после записи может не вернуться, хотя планшет уже
перезагрузился; тогда его процесс снимают. Планшет загружается в Android:
дождаться `sys.boot_completed=1`, затем `adb reboot recovery` — это Linux.

## 5. Первая загрузка

`haltia-firstboot` ставит пакеты из кэша, копирует прошивки из `vendor_b` и
`modem_b` и растягивает корень. 27 октября первая загрузка превысила
`deferred_probe_timeout=60`: GPU не привязался, панель упала, тач-драйвер
упал вслед (#24), а `reboot` завис — спасло долгое нажатие питания. Теперь
таймаут 120 с. Вторая и следующие загрузки проходят за ~45 с.

После установки: подключить Wi-Fi (сети не переносятся), проверить звук,
тач, камеру (`cam -l`), двойной тап, Android на `_b`.

## Мелкая правка ядра или DTB

Без переустановки: собрать DTB или модуль в рабочем дереве, затем

```
TABLET=10.15.0.2 /mnt/data/tmp/j606l-v2/to-fastboot.sh
fastboot flash recovery_b haltia-boot.img && fastboot reboot
```

`to-fastboot.sh` делает `haltia-boot linux` и перезагрузку в загрузчик.
Перед ним закрыть камеру: 27 октября перезагрузка с открытой камерой
зависла. Модуль можно положить в `/lib/modules/<версия>/updates/` и
выполнить `depmod -a`.
