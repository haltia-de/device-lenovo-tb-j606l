# Досье TB-J606L

Снято 23 октября 2026 с лабораторного экземпляра по USB. Только чтение.
Серийный номер сюда не входит. План —
[tab-p11.md](https://github.com/haltia-de/haltia/blob/main/docs/plans/tab-p11.md).

## Плата

| | |
|---|---|
| Модель | Lenovo TB-J606L, `LenovoTB-J606L_RU`, устройство `J606L` |
| SoC | Qualcomm `bengal`, SM6115, userspace aarch64 |
| Android | 11, `TB-J606L_S320317_230810_ROW`, ядро производителя 4.19.157 |
| Загрузчик | `verifiedbootstate=green`, `flash.locked=1`, `vbmeta` locked. `sys.oem_unlock_allowed=1` |
| Слот | `ro.boot.slot_suffix=_b`. A/B и динамические разделы включены |
| Корень Android | dm-verity слота B: `system`, `system_ext`, `vendor`, `product` |
| Данные | `userdata` — f2fs через device-mapper, около 102 ГБ. В момент чтения занято около 45 ГБ. Разблокировка это стирает |

Разделы, которые видны по именам: `boot_a`/`boot_b`, `dtbo_a`/`dtbo_b`,
`vbmeta_a`/`vbmeta_b`, `vbmeta_system_a`/`vbmeta_system_b`,
`recovery_a`/`recovery_b`, `super`, `userdata`, `modem_a`/`modem_b`,
`modemst1`, `modemst2`, `fsg`, `fsc`, `persist`. Прочитать заголовок
`boot_a` без root нельзя (`Permission denied`). Жив ли слот A как
Android, с этого сеанса не видно. Перезагрузка в fastboot не делалась.

Прошивки модема слота B смонтированы в Android: `modem_b`, `dsp_b`,
`bluetooth_b`.

## Экран и ввод

Физически 1200×2000 при 60 Гц, плотность 240. Подсветка
`panel0-backlight`. Узел DRM `card0-DSI-1`. Имя панели в Android пустое.
Режимы DRM и дерево устройства побайтно не читаются: каталог
`/proc/device-tree` виден, файлы `compatible` и `model` закрыты.

Касание: `NVTCapacitiveTouchScreen`, шина `0x001c`, vendor 0, product 0.
Перо: `NVTCapacitivePen`. В системе лежит `Vendor_04f3_Product_3164.idc`
(Elan). К устройству касания он не привязан: у касания своего idc нет.

Ещё: `qpnp_pon`, `gpio-keys`, холл, гарнитура `bengal-idp-snd-card`,
пого-узел `mcu_pogo` по HID.

## Имена узлов питания и звука

Усилители `aw882xx` на адресах `0x34`–`0x37`. Кодек `es7210` (`0x42`
на второй шине). Коммутатор гарнитуры `fsa4480`. USB-C `fusb302`.
Измеритель `mm8013`. Подсветка `sgm37604a`. Батарея в момент чтения
была в состоянии Charging.

## Кнопки

На этом экземпляре сочетания не проверялись: проверка выключает Android.

Публичная инструкция для TB-J606L и TB-J606F описывает fastboot так:
выключить планшет, удерживать громкость вниз и питание, пока не появится
загрузчик. Режим EDL в той же инструкции: выключить, удерживать
громкость вверх и подключить кабель. Это не проверка нашего экземпляра.
Пока загрузчик не подтвердит своё меню, аварийный ход в плане остаётся
fastboot с компьютера.

## Основное ядро

В Linux (дерево на октябрь 2026) есть только
`arch/arm64/boot/dts/qcom/sm6115p-lenovo-j606f.dts`. Модель в нём —
Wi-Fi J606F:

- `compatible = "lenovo,j606f", "qcom,sm6115p", "qcom,sm6115"`
- загрузчик выбирает плату по `qcom,msm-id = <445 0x10000>, <420 0x10000>`
  и `qcom,board-id = <34 3>`
- simplefb 1200×2000, формат `a8r8g8b8`, и панель
  `lenovo,j606f-boe-nt36523w`, `novatek,nt36523w` (драйвер
  `panel-novatek-nt36523.c` в том же ядре)
- кнопки питания и громкости, SD, USB 2.0
- прошивки ADSP, CDSP, модема и GPU zap по пути `qcom/sm6115/LENOVO/J606F/`
- узла касания, зарядки и звука `aw882xx` в этом dts нет

Отдельного dts для J606L нет. Образ, собранный из дерева J606F, на этот
планшет не ставится, пока не сверены `msm-id` и `board-id`.
