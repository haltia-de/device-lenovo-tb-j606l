# Камеры TB-J606L

Исследование 27 октября 2026. Issue #22.

## Датчики

| | Фронтальная | Основная |
|---|---|---|
| Датчик | OmniVision OV8856, id `0x885a` (рег. `0x300b`) | OmniVision OV13B10, id `0x560d42`, модуль `0x7d9` |
| CCI | master 1 (GPIO 29/30), адрес `0x36` в Linux | master 0 (GPIO 22/23), адрес `0x10` |
| CSI | CSIPHY2 (`0x5c54000`, IRQ 74), 4 линии | CSIPHY0 (`0x5c52000`, IRQ 72) |
| MCLK | MCLK2, GPIO 27, 19,2 МГц | MCLK0, GPIO 20, 19,2 МГц |
| Сброс | GPIO 19, активный низкий | GPIO 18, активный низкий |
| Прочее | — | VAF (автофокус) на GPIO 40, актуатор, вспышка, EEPROM |

Питание обоих датчиков — GPIO 112 (в стоке `CAM_VANA`) и GPIO 108
(`CAM_VDIG`), обе включаются высоким уровнем. Регуляторов нет: PMIC PM8008
на этой плате отсутствует, хотя стоковое дерево ссылается на `L2P/L4P/L7P`.

Android при открытии фронтальной камеры (лог драйвера камеры с
`debug_mdl`, root через Magisk): `RESET(19)=0`, `GPIO112=1`, `GPIO108=1`,
MCLK 19,2 МГц, 10 мс, `RESET(19)=1`. В стоковом сенсорном
драйвере адрес фронтальной — `sid 0x10` (8 бит `0x20`). В Linux OV8856 отвечает
на `0x36` (и `0x21`), но не на `0x10`. Режим, который ставит Android:
`0x3018=0x72` (4 линии), `0x4837=0x16`. Это режим 3280x2464 драйвера mainline.

## Почему датчики не отвечали

GPIO 98–112 на SM6115 — eGPIO. Пока в регистре управления пина не выставлен
бит `EGPIO_ENABLE` (бит 12, бит 11 — «eGPIO есть»), падом владеет другая
подсистема, и выход TLMM на ногу не попадает: регистр показывает
`out 1`, а вход читается `0`. Android бит ставит, `pinctrl-sm6115` в
mainline о нём не знал. Поэтому питание на датчики не приходило, и CCI
получал NACK при правильной последовательности.

Проверено и исключено до этого: тайминги CCI (стоковые `hw-thigh`… совпадают
с `cci_v2_data` mainline один в один), частота CCI 37,5 МГц, полярности
GPIO, сила тока пинов, 100 и 400 кГц. Добавление `GCC_CAMSS_AXI_CLK` в узел
CCI без голоса интерконнекта роняет SoC в EDL (900e).

## Что сделано

- Патч `0009-pinctrl-sm6115-egpio.patch`: функция `egpio` для GPIO 98–112 и
  `egpio_func = 9`, как у QCM2290. Ядро ставит бит само, когда пин берут как GPIO.
- Патч `0010-media-camss-add-sm6115.patch`: `qcom,sm6115-camss` — CSID и TFE
  от QCM2290 (TFE 340) и третий CSIPHY.
- Патч `0011-media-ov8856-keep-bayer-order.patch`: `get_format` и `open()`
  драйвера OV8856 сбрасывали выбранный порядок Байера на режим по
  умолчанию. libcamera просила BGGR, датчик отдавал GRBG, и запуск потока
  падал с `EPIPE`.
- Патч `0012-media-camss-csiphy-settle-mid-window.patch`: CSIPHY ждал только
  минимум T_HS-SETTLE (85 нс + 6 UI). На 180 МГц (режимы 1640x1232) CSID
  считал ошибки CRC и ECC на каждом пакете, кадров не было. Середина окна
  D-PHY (115 нс + 8 UI) работает на 180 и 360 МГц.
- DTS: CCI, CAMSS (по образцу `agatti.dtsi`), фиксированные регуляторы на
  GPIO 112/108, OV8856 (`link-frequencies` 360 и 180 МГц, `rotation = 90`: `haltia_kit` поворачивает
  картинку на это и на поворот экрана из `$XDG_RUNTIME_DIR/haltia/rotation`,
  потом зеркалит. Проверено на планшете: 0 — верх вправо, 270 (как
  `sensor-position-roll` в стоке) — вверх ногами, 90 — прямо).
- Конфиг: `VIDEO_QCOM_CAMSS`, `I2C_QCOM_CCI`, `VIDEO_OV8856`, кучи DMA-BUF.
  В cmdline `cma=256M`: программный ISP берёт буферы из CMA, 32 МБ не хватало.
- Rootfs: `libcamera`, `libcamera-ipa`, `libcamera-tools`,
  `libcamera-gstreamer`; правило `84-j606l-camera.rules` отдаёт
  `/dev/dma_heap/*` группе `video`.

## libcamera

Конвейер `simple` с программным ISP (libcamera 0.7.1, отладка Байера на GPU):

```
cam -l
cam -c1 --capture=30 -s width=1632,height=1224          # 30 к/с
gst-launch-1.0 libcamerasrc ! video/x-raw,width=1280,height=720 ! videoconvert ! ...
```

1632x1224 и 1640x1232 идут 30 к/с; 3264x2448 — 10 к/с на GPU, 3,3 к/с с
`LIBCAMERA_SOFTISP_MODE=cpu`. Для OV8856 в libcamera нет sensor helper и
файла калибровки (`uncalibrated.yaml`): AGC сходится за несколько десятков
кадров, цвета без калибровки.

Сырой кадр без libcamera:

```
S=$(media-ctl -p | grep -o "ov8856 [0-9]-0036" | head -1)
media-ctl -l '"msm_csiphy2":1->"msm_csid0":0[1],"msm_csid0":1->"msm_vfe0_rdi0":0[1]'
F="SGRBG10_1X10/3280x2464 field:none"
media-ctl -V "\"$S\":0[fmt:$F],\"msm_csiphy2\":0[fmt:$F],\"msm_csid0\":0[fmt:$F],\"msm_vfe0_rdi0\":0[fmt:$F]"
v4l2-ctl -d /dev/video0 --set-fmt-video=width=3280,height=2464,pixelformat=pgAA \
	--stream-mmap --stream-count=5 --stream-to=front.raw
```

Кадр — MIPI RAW10 с шагом строки 4104 байта, GRBG. Номер шины I2C у
датчика меняется от загрузки к загрузке.

Осторожно: перезагрузка с открытой камерой зависла после остановки тача
(27 октября); перед `reboot` камеру закрыть.

Осторожно: чтение регистров CSID через `/dev/mem`, когда у CAMSS сняты
такты, роняет SoC в EDL (900e).

## Что осталось

- Основная OV13B10: в драйвере `ov13b10` нет таблицы OF (только ACPI),
  нужен патч, плюс CSIPHY0, MCLK0, сброс GPIO 18, VAF GPIO 40. Автофокус,
  вспышка и EEPROM — позже.
- Голоса интерконнекта и такты AXI задаёт CAMSS; в CCI их не добавлять.
- Sensor helper и калибровка OV8856 для libcamera, приложение камеры в оболочке.
- В `dmesg` идёт поток `qcom_q6v5_pas a400000.remoteproc: Handover signaled,
  but it already happened` — с камерами не проверено.
