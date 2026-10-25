# Диагностический RAM/USB-образ TB-J606L

Исходники для задачи [№ 5](https://github.com/haltia-de/device-lenovo-tb-j606l/issues/5).
Это промежуточный этап порта: Linux, статический PID1 и ранний журнал по USB ACM.
Рабочего стола и постоянного Linux rootfs в образе пока нет.

Ядро закреплено на `7dd245445adf6eaa27018cf92fbd5a92ec0b118e`
из `TeamYogaBlade2/linux`, версия 7.1.0. Это fork pin, а не утверждение
о равенстве всего дерева официальному Linux. Сравнение конкретных DTS
зафиксировано в `source-comparison.json`. Firmware периферии не требуется:
GPU, MDSS, накопитель, модем, ADSP/CDSP и Wi-Fi отключены. `CONFIG_BLOCK=n`.
Исходный J606F DTS служит сравненной основой; ID SoC заменён на измеренный 444.
Board-id 34/3 — метаданные выбранного штатного LTE PVT overlay, не прямое
измерение регистра платы. Физическая DSI-панель пока не установлена.

## Чистая сборка

Нужны Docker, git, RTK и Python 3.12 с поддержкой `tarfile` data filter.
Проверенная упаковочная среда: CPython 3.12.3, zlib 1.3, x86_64 Linux.
Версии Python/zlib записываются в manifest; побайтовое равенство между
произвольными версиями упаковщика не заявляется. Нужно не менее 12 GiB
свободного места; контейнер ограничен 4 CPU и 8 GiB RAM.

Из этого каталога:

```sh
rtk proxy git clone --filter=blob:none --no-checkout https://github.com/TeamYogaBlade2/linux.git /tmp/j606l-linux
rtk proxy git -C /tmp/j606l-linux checkout --detach 7dd245445adf6eaa27018cf92fbd5a92ec0b118e
rtk proxy docker build --platform linux/amd64 --iidfile /tmp/j606l-toolchain.id -f Dockerfile.toolchain .
```

Рецепт начинает с официального digest Ubuntu, устанавливает закреплённый
пакет сертификатов из подписанного архива, затем использует подписанный
snapshot Ubuntu. Полный список 179 пакетов должен совпасть с
`toolchain-packages.lock.tsv`. TLS и проверка подписей остаются включены.
Сеть нужна для получения исходников и toolchain; сама компиляция изолирована
от сети и USB, без capabilities и с исходниками только для чтения.

В следующих командах замените `sha256:<IMAGE_ID>` точным значением из
`/tmp/j606l-toolchain.id`:

```sh
rtk proxy python3 -B offline_tests.py --image sha256:<IMAGE_ID> --work /tmp/j606l-tests
rtk proxy python3 -B build.py --build --source /tmp/j606l-linux --work /tmp/j606l-build --image sha256:<IMAGE_ID>
rtk proxy python3 -B check_dtb.py --work /tmp/j606l-build
rtk proxy python3 -B package.py --work /tmp/j606l-build
```

Результат: `/tmp/j606l-build/package/boot-j606l-ramdiag.img` и приватные
manifests с фактическими хэшами. В исходный каталог не записываются kernel tree,
резервы или готовые образы. Старое значение toolchain ID в build-ID seed —
явный стабильный seed протокола; фактически использованный image ID записан
отдельно и проверен по полному inventory. Это не ссылка на опубликованный image.

## Проверенный локальный результат

Замороженный прототип: 2056192 байта, SHA256
`a9990c894d1a60f6bd06140cd34e6aa848b9880094059a6ba5780a2051ea4ff2`,
build ID `haltia-j606l-11d85e24d551ea08`.
Независимая чистая сборка и упаковка исходного прототипа совпали побайтово.
Упаковка сохраняет штатный header v2, адреса, Android 11.0.0 и security patch
2023-07; rollback metadata не добавляется. Сам штатный образ не распространяется.

13 Python-тестов и C/PTY-проверки покрывают whitelist CPIO, заголовок,
proof parser, короткие записи, EAGAIN, deadlines, ограничение журнала,
LF/CR/NUL и hotplug-привязку наблюдателя. Они не запускают PID1 на компьютере
и не открывают планшет. Новая реконструкция toolchain успешно собрана.
Независимая чистая сборка по этому переносимому рецепту, статическая
проверка DTB и двойная упаковка прошли; полный boot-образ снова совпал
с указанным замороженным прототипом. На восстановленном toolchain
повторно прошли все 13 Python-тестов и C/PTY-проверки.

## Аппаратная проба — отдельный этап

`watch_usb.py` — библиотека наблюдения, не контроллер загрузки. Запуск файла
не обращается к USB. PID1 передаёт повторяемые proof/log кадры не дольше
90 секунд, затем один раз просит перезагрузку в bootloader. Это ещё не
доказанный возврат в Android. Ранняя паника останавливается (`panic=0`).

Новый Linux на планшете пока не запускался. Штатный DTBO и изменения A/B
metadata могут влиять даже на downloaded boot. Сценарий первой пробы,
привязанный к точному образу и резервам, должен отдельно пройти проверку:
[план первой RAM-загрузки](https://github.com/haltia-de/haltia/blob/main/docs/plans/j606l-first-ram-boot.md).
Старые retired J606F one-shot не используются.

## Происхождение

`mkbootimg.py` — неизменённый AOSP файл с сохранённой Apache-2.0 шапкой,
SHA256 `5579fb6bcb9e89e790a70fb9ccf3c00cf56e3e46aef74d84fcb0964887e5576e`.
Код PID1/I/O отмечен MIT, DTS — GPL-2.0+ OR BSD-3-Clause.
Лицензия корневого репозитория сохраняется. Приватные дампы, USB serial,
логи экземпляра и материалы Android в эту поставку не входят.

Развёрнутый локальный draft с измеренными flags, reference ALL_BITS_SET и ещё не доказанными downloaded/A-only вариантами: [FIRST-TEST.md](FIRST-TEST.md). Исполняемого boot/flash/slot controller в дереве нет.
