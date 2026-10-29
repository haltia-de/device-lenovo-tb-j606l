# Апстрим работы порта TB-J606L

Исследование 28 октября 2026. Здесь разобрано, куда можно отдать ядро и
описание железа из этого репозитория и как каждый проект принимает
изменения. Ничего не отправлено, никто не уведомлён.

## Как проверяли

- Ядро порта: `TeamYogaBlade2/linux` `blade/v7.1` (`kernel/README.md:3`).
  Это форк для планшетов MT6589 («Near-mainline Linux kernel for Lenovo YOGA
  Tablet 8/10 with additional MT6589 support»,
  https://github.com/TeamYogaBlade2/linux), поэтому для SM6115 он равен
  Linux 7.1. Чистое дерево лежит в `/mnt/data/tmp/j606l-src-7dd2454`, дерево с
  патчами в `/mnt/data/tmp/j606l-r4/linux`.
- Сопровождающих искали через `scripts/get_maintainer.pl --no-git` по каждому
  патчу и по файлу `MAINTAINERS` этого дерева.
- Состояние mainline смотрели в `torvalds/linux.git` (master — 7.3-rc,
  https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/plain/Makefile)
  и в тегах `v7.2` и `v7.3-rc1`.
- lore.kernel.org не пускает автоматические запросы (страница Anubis «Making
  sure you're not a bot»). Серии искали через REST API patchwork
  (`https://patchwork.kernel.org/api/1.3/patches/?q=…`), ссылки ниже ведут на
  lore по Message-ID.

## Общие правила для ядра

Они касаются каждого патча ниже.

- Порядок подачи описан в `Documentation/process/submitting-patches.rst`
  (`/mnt/data/tmp/j606l-r4/linux/Documentation/process/submitting-patches.rst`):
  одно логическое изменение на патч (`:168`), `checkpatch` (`:201`),
  получатели из `get_maintainer.pl` (`:231`), только текст без вложений
  (`:278`), ответы на ревью (`:310`).
- Signed-off-by и DCO 1.1 (`submitting-patches.rst:396`, `:409`). Пункт (b)
  разрешает код, основанный на чужой работе под открытой лицензией (`:418`):
  это путь для кода из GPL-исходников Lenovo, Awinic и Everest.
- Все патчи порта писались с Claude: 13 коммитов с патчами несут
  `Co-Authored-By: Claude …` (`git log -- kernel/patches`). Ядро требует
  тег `Assisted-by: AGENT_NAME:MODEL_VERSION` вместо этого
  (`submitting-patches.rst:637-645`). ИИ не ставит Signed-off-by: его ставит
  человек, который прочёл код и отвечает за него
  (`Documentation/process/coding-assistants.rst:27-46`). Перед отправкой
  каждый патч должен перечитать и подписать Михаил.
- Биндинги DT идут отдельным патчем впереди драйвера, с префиксом
  `dt-bindings: <dir>:`. ASoC и media пишут префиксы наоборот
  (`Documentation/devicetree/bindings/submitting-patches.rst:14-22`). Каждый
  новый `compatible` нужно описать в YAML, и схема должна пройти
  `make dt_binding_check` (`:39`).
- Сначала патчи переносят на `linux-next` или дерево сопровождающего:
  в 7.2 и 7.3 часть работы уже сделана (см. ниже).
- Списки рассылки: общий для Qualcomm — `linux-arm-msm@vger.kernel.org`
  (`MAINTAINERS:3326`, Bjorn Andersson, Konrad Dybcio). Для биндингов —
  `devicetree@vger.kernel.org` (`MAINTAINERS:20009`, Rob Herring, Krzysztof
  Kozlowski, Conor Dooley).

## Сводка

Статус: **есть** — уже в mainline; **частично** — драйвер или серия есть,
нашего железа в них нет; **на рассмотрении** — открытая серия на lore;
**нет** — в апстриме ничего.

| Что | Куда | Сопровождающие, список | Статус | Работа, препятствия |
|---|---|---|---|---|
| `0009` eGPIO SM6115 | pinctrl/qcom | Bjorn Andersson, Linus Walleij; linux-arm-msm, linux-gpio | **есть** с v7.2 | Убрать патч при переходе на ≥7.2 |
| `0017` psci-cpuidle после отложенных probe | cpuidle | Ulf Hansson и др.; linux-pm | **есть** в master (после 7.3-rc1) | Убрать патч. Ждать бэкпорт (`Cc: stable`) |
| `0016` fastrpc: прерванный вызов | misc/fastrpc | Srinivas Kandagatla, Amol Maheshwari; linux-arm-msm, dri-devel | **на рассмотрении** (Qualcomm, v3) | Проверить v3 на планшете, отправить `Tested-by`. Своё не слать |
| `0014` nt36523: панель при сбое attach | drm/panel | Jianhua Lu, Neil Armstrong; dri-devel | **на рассмотрении** (другой автор) | Отправить `Tested-by` к чужому патчу |
| `0011` ov8856: порядок Байера | media/i2c | Sakari Ailus; linux-media | **нет**, ошибка есть в master | Малая. Хороший первый патч |
| `0013` smp2p-sleepstate | soc/qcom + биндинг | Bjorn Andersson, Konrad Dybcio; linux-arm-msm | **частично**: биндинг на рассмотрении (Acayan), драйвера нет | Средняя. Код из даунстрима, нужен новый биндинг |
| MPM в `sm6115.dtsi` | arm64 DTS qcom | Bjorn, Konrad; linux-arm-msm | **частично**: карта пинов есть, узла нет | Малая/средняя, по образцу QCM2290 |
| `0004` dwc3-qcom: QSCRATCH после resume | usb/dwc3 | Thinh Nguyen, Greg KH; linux-usb, linux-arm-msm | **нет** (ни в legacy, ни в новом драйвере) | Малая. Исправить и `dwc3-qcom.c` |
| `0010` CAMSS SM6115 | media/qcom/camss + биндинг + dtsi | Robert Foss, Todor Tomov, Bryan O'Donoghue; linux-media | **нет** | Средняя: YAML, узлы CAMSS/CCI в `sm6115.dtsi` |
| `0012` CSIPHY settle | media/qcom/camss | те же | **нет** | Меняет поведение всех SoC. Только RFC с замерами |
| `0003` SGM37604A | backlight + биндинг | Lee Jones, Daniel Thompson, Jingoo Han; dri-devel | **нет** | Малая/средняя: YAML, настройка без загрузчика |
| `0006` AW88258 | ASoC codecs (`aw88261`) | Liam Girdwood, Mark Brown; linux-sound | **частично**: `aw88261` есть, AW88258 не распознаёт | Средняя: переписать как вариант `aw88261` |
| `0007` ES7210 | ASoC codecs + биндинг | Liam Girdwood, Mark Brown; linux-sound | **нет** | Малая польза: ES7210 не на пути микрофонов |
| `0007` SEC_MI2S_TX в `sm8250.c` | ASoC qcom | Srinivas Kandagatla; linux-sound, linux-arm-msm | **нет** | Как есть нельзя: зашито для всех плат |
| `0001`/`0002`/`0005`/`0008` тач NT36523W | input/touchscreen + биндинг | Dmitry Torokhov; linux-input | **нет** (попытки 2020–2024 не влиты) | Большая: переписать вендорский драйвер |
| `0008`, часть панели | drm/panel | Jianhua Lu, Neil Armstrong; dri-devel | **нет** | Нужно обсуждение TDDI в DRM |
| `0015` fastrpc: пробуждение | misc/fastrpc | как у `0016` | **нет** | Средняя, сначала RFC |
| DBMD8 | ASoC codecs, новый драйвер | ASoC; linux-sound | **нет** | Очень большая. Сейчас userspace + spidev-хак |
| `sm6115-lenovo-j606l.dts` | arm64 DTS qcom | Bjorn, Konrad; linux-arm-msm, devicetree | **нет** (J606F есть) | Средняя. Общий `.dtsi` с J606F, только описанные биндинги |
| Пакет устройства | postmarketOS/Nura pmaports | MR на gitlab.postmarketos.org | **нет** (нет ни J606F, ни J606L) | Средняя. Ядро `sm61x5-mainline` |
| `rootfs/ucm` | alsa-ucm-conf | PR на GitHub | **нет** | Малая, после драйверов в ядре |
| `81-j606l-sensors.rules` | iio-sensor-proxy, pmaports | MR на freedesktop GitLab | **на рассмотрении** (MR 409) | Отзыв к MR 409. Матрица — в пакет устройства |
| `haltia-rtc` | swclock-offset (pmaports) | — | **есть** аналог | Взять swclock-offset или ядерный offset |
| Прошивки Lenovo | linux-firmware | — | **нельзя** | Нет лицензии Lenovo на распространение |

## Ядро: уже в апстриме

### `0009` eGPIO на SM6115 — в mainline

Коммит `0524a508b2cf` «pinctrl: qcom: sm6115: Add egpio support» Станислава
Заикина: https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/commit/?id=0524a508b2cf7a3819406cd10d43d6e30fa31004
(серия: https://lore.kernel.org/r/20260522141149.1425711-1-zstaseg@gmail.com).
Код совпадает с нашим: `egpio_enable = 12`, `egpio_present = 11`, группа
`gpio98`–`gpio112` (`kernel/patches/0009-pinctrl-sm6115-egpio.patch`;
`pinctrl-sm6115.c?h=v7.2`, строки 457-461). Он есть в `v7.2`, в чистом 7.1
его нет. При переходе на 7.2 патч `0009` убрать. Наш вклад здесь — пример
использования: камеры J606L питаются от GPIO 108 и 112 (`docs/camera.md:30`).

### `0017` psci-cpuidle — исправлено в mainline

Ulf Hansson убрал faux-устройство, с которым ломались отложенные probe:
«cpuidle: psci: Fix support for probe deferral by dropping the faux device»
(`Cc: stable`,
https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/commit/?id=0606f2114e2dc88fe293858fd991cda2688b8c3a).
Следом он перенёс инициализацию в `subsys_initcall`
(https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/commit/?id=65705b18162bbf0771adf742ee528521957fb496).
В `v7.3-rc1` осталось `device_initcall` с faux. Значит, исправление пришло
позже, и с бэкпортом в stable дойдёт до 7.1/7.2. Наш `late_initcall_sync`
(`kernel/patches/0017-…:22`) обходит ту же ошибку. В апстрим его не
отправлять, а при переходе на ядро с этим исправлением убрать. Полезно:
проверить исправление на J606L с MPM как родителем кластеров и написать в
ветку Ульфа, если оно не помогает.

## Ядро: на рассмотрении у других

### `0016` fastrpc: прерванный вызов

Qualcomm прислала то же исправление: «[v3] misc: fastrpc: fix context leak
and hang on signal-interrupted invoke», Anandu Krishnan E, 1 октября 2026,
https://lore.kernel.org/r/20261002-anandu-fastrpc-interrupted-invoke-v3-v3-1-31e90439d2ba@oss.qualcomm.com
(v1 от мая, v2 от июля). Описан тот же сбой: повторная отправка после
`-ERESTARTSYS` даёт DSP дубликат вместо ответа на обратный вызов, и поток DSP
зависает. Решение то же: контекст паркуется и подхватывается при повторе.
v3 надёжнее нашего `0016`. Он сравнивает `handle` и `sc`, а не только `sc`,
хранит свою копию `args` и чистит контексты при выходе процесса и SSR. В
нашем патче контекст сверяется только по `pid` и `sc`
(`0016-…:39-50`).

Что сделать: собрать ядро с v3 вместо `0016`, повторить тест D из
`docs/sleep.md` (s2idle 300 с с `hexagonrpcd`) и ответить на lore
`Tested-by:` с описанием (SM6115, `adsp_listener`, крах
`EX:sensor_process:0x1:frpc_dsp`). Такой отчёт от пользователя на другом SoC
очень полезен сопровождающим (`submitting-patches.rst:551`). Сопровождающие
fastrpc: Srinivas Kandagatla, Amol Maheshwari (`MAINTAINERS:21941`).

### `0014` nt36523: панель при сбое DSI attach

Myeonghun Pak и Ijae Kim прислали «[2/2] drm/panel: novatek-nt36523: use
devm_drm_panel_add()» (24 мая 2026, `Fixes:` и `Cc: stable`),
https://lore.kernel.org/r/c6fe4a162692b4df5525353dbdac5b88eda91a79.1779640137.git.mhun512@gmail.com.
Это общее решение. `devm_drm_panel_add` снимает панель с учёта при любой
ошибке probe, и `.remove` больше не нужен. Наш `0014` исправляет только
путь attach. В master ошибка ещё есть: `drm_panel_add`, потом
`return dev_err_probe(...)` без удаления
(`panel-novatek-nt36523.c`, master, строки 1229-1238). Патч в patchwork
висит в состоянии «new» пять месяцев. Ответ с `Tested-by:` и описанием
нашего реального oops (issue #24, `docs/sleep.md`, раздел «Падение тача»)
даст ему ход. Сопровождающий драйвера — Jianhua Lu (`MAINTAINERS:8173`),
дерево drm-misc.

## Ядро: можно отправить своё

### `0011` ov8856: сохранить порядок Байера

В master ошибка на месте: `ov8856_update_pad_format` пишет
`cur_mbus_index = index` (`drivers/media/i2c/ov8856.c`, master, строка
1993), `get_format` и `open()` сбрасывают выбранный формат. Наш патч
небольшой, и сбой легко воспроизвести (libcamera, BGGR, `EPIPE`;
`kernel/patches/0011-…:1-9`). Автор драйвера на lore активен: в 2026 году
в него вошли правки Intel и Koskovich
(https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/log/drivers/media/i2c/ov8856.c).
Сопровождающий — Sakari Ailus, linux-media (`MAINTAINERS:19871`). Перенести
на master: сигнатура pad ops изменилась в 7.3
(`v4l2_subdev_client_info`, коммит `7eef49c16461` в том же логе).
Препятствий нет. Нужны `Fixes:` на коммит, который ввёл `cur_mbus_index`, и
прогон `v4l2-compliance`.

### `0004` dwc3-qcom: QSCRATCH после resume

`sm6115.dtsi` в mainline описывает USB старым биндингом
(`qcom,sm6115-dwc3` + дочерний `snps,dwc3`; `sm6115.dtsi`, master, строки
1638-1679). Поэтому работает `dwc3-qcom-legacy.c`, «снимок для обратной
совместимости»
(https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/commit/?id=b958b03c82d2a1c470225355e43248c679a949a5).
В новом `dwc3-qcom.c` выбор UTMI-тактов и VBUS override тоже делаются только
в probe (master, строки 684 и 692), не в resume. Значит, исправление нужно в
обоих файлах. Иначе сопровождающий попросит сначала перевести `sm6115.dtsi`
на новый биндинг: в `qcom,snps-dwc3.yaml` `qcom,sm6115-dwc3` уже есть.
Получатели: Thinh Nguyen, Greg Kroah-Hartman, linux-usb, linux-arm-msm
(`get_maintainer.pl` для `dwc3-qcom.c`). Нужно заодно проверить, что
mainline J606F (без `qcom,select-utmi-as-pipe-clk`,
`sm6115p-lenovo-j606f.dts`, master, строки 357-368) ведёт себя так же. У нас
это свойство ставит `kernel/sm6115-lenovo-j606l.dts:105`.

### MPM для SM6115

Карта пинов MPM в `pinctrl-sm6115.c` уже есть (`sm6115_mpm_map`, master,
строка 876; серия Konrad Dybcio 2023,
https://lore.kernel.org/r/20230809-topic-mpm_mappings-v2-2-4c2b4495e654@linaro.org).
Узла `qcom,mpm` в `sm6115.dtsi` нет (master, `grep mpm` пуст). У QCM2290 его
добавили в 2023 году: «arm64: dts: qcom: qcm2290: Hook up MPM»,
https://lore.kernel.org/r/20231215-topic-mpm_dt-v1-3-c6636fc75ce3@linaro.org.
Наш узел, MPM как родитель кластеров и `wakeup-parent`
(`kernel/sm6115-lenovo-j606l.dts:864-911`) надо перенести в `sm6115.dtsi`. Это
изменение SoC, оно касается и RB2, и Fxtec Pro1X, и J606F. Препятствия:
- полную карту пинов надо взять из даунстрима `qcom-mpm-bengal.c`, у нас
  только шесть пинов (`:891-896`);
- пин 91 делит GIC 260 с пином 90, mainline не принимает такой дубль
  (`docs/sleep.md`, раздел MPM). Это надо описать в письме;
- без исправления psci-cpuidle (см. `0017`) cpuidle перестаёт работать. В
  письме указать зависимость от коммита Ульфа.
Список: linux-arm-msm, Bjorn Andersson и Konrad Dybcio (`MAINTAINERS:3326`).

### `0003` SGM37604A

В mainline драйвера и биндинга нет (`drivers/video/backlight/` 7.1;
patchwork по «sgm37604» пусто). Префикс `sgmicro` есть
(`Documentation/devicetree/bindings/vendor-prefixes.yaml:1468` в дереве 7.1).
Нужно:
- YAML `Documentation/devicetree/bindings/leds/backlight/sgmicro,sgm37604a.yaml`;
- драйвер сейчас полагается на настройку загрузчика: строки, ток, режим
  (`0003-…:6-10`). Апстрим захочет хотя бы чтение `enable-gpios` и
  настройку из DT или явный текст, что драйвер работает только в режиме
  «после загрузчика». Узел у нас без `enable-gpios`
  (`kernel/sm6115-lenovo-j606l.dts:268-271`);
- связь с панелью. Mainline J606F берёт яркость через DCS
  (`j606f_boe_desc.has_dcs_backlight = true`, `panel-novatek-nt36523.c`,
  master, строка 981). На J606L яркость реально задаёт SGM37604A. Если на
  J606F стоит та же микросхема, это исправление и для J606F. Тогда DTS
  задаёт `backlight = <&…>` у панели, а драйвер панели перестаёт
  регистрировать DCS-подсветку для этого `compatible`.
Получатели: Lee Jones, Daniel Thompson, Jingoo Han, dri-devel,
linux-fbdev (`MAINTAINERS:4413`).

### `0010` CAMSS на SM6115

Ни драйвера, ни биндинга, ни узлов в `sm6115.dtsi` нет: patchwork по
«sm6115 camss», «qrb4210 camss» пусто, `camss.c` в master не знает
`sm6115`. QCM2290 есть (`qcom,qcm2290-camss.yaml`; `camss.c` 7.1, строка
5151). Наш патч добавляет `qcom,sm6115-camss` с третьим CSIPHY
(`0010-…:1-4`). Для апстрима нужны:
1. `dt-bindings: media: qcom,sm6115-camss` — новый YAML: у SM6115 есть
   `csiphy2`, `csiphy2_timer` и третье прерывание, поэтому фолбэк на
   `qcom,qcm2290-camss` не подходит;
2. `media: qcom: camss: Add SM6115` — наш патч;
3. узлы `camss` и `cci` в `sm6115.dtsi`. CCI у нас висит в DTS платы с
   `qcom,qcm2290-cci` (`kernel/sm6115-lenovo-j606l.dts:687`). Апстрим захочет
   `qcom,sm6115-cci` в `qcom,i2c-cci.yaml`;
4. узел датчика в DTS платы.
Получатели: Robert Foss, Todor Tomov, Bryan O'Donoghue, Vladimir
Zapolskiy, linux-media, linux-arm-msm (`MAINTAINERS:21863`). Риск: тактовая и
интерконнектная часть из `docs/camera.md` («Голоса интерконнекта и такты AXI
задаёт CAMSS») проверена на одной плате.

### `0012` CSIPHY settle — только RFC

Патч меняет `t_hs_settle` для всех SoC на `csiphy-3ph-1-0`
(`camss-csiphy-3ph-1-0.c`, master, строки 1016-1017). Bryan O'Donoghue уже
вводил отдельную задержку settle для X1E80100: «Add support for 3ph CSIPHY
write settle delay»,
https://lore.kernel.org/r/20250314-b4-media-comitters-next-25-03-13-x1e80100-camss-driver-v2-5-d163d66fcc0d@linaro.org.
Сопровождающие вряд ли примут общую замену без замеров на других
платформах. Подавать как RFC с цифрами из `docs/camera.md` (CRC и ECC на
180 МГц, рабочие 180 и 360 МГц) и с вариантом «на SoC или из DT».

### `0013` smp2p-sleepstate

Биндинг: Richard Acayan прислал «dt-bindings: soc: qcom,smp2p: add sleepstate
support» в серии для SDM670 (v2, 3 октября 2026, `Acked-by` Krzysztof
Kozlowski),
https://lore.kernel.org/r/20261003175659.23536-2-mailingradian@gmail.com.
Патч только разрешает подузел `sleepstate` в `qcom,smp2p.yaml`, драйвера в
серии нет (обложка:
https://patchwork.kernel.org/project/linux-arm-msm/cover/20261003175659.23536-1-mailingradian@gmail.com/).
Наш драйвер — первая реализация, но:
- `compatible = "qcom,smp2p-sleepstate"` в корне дерева
  (`kernel/sm6115-lenovo-j606l.dts:856-861`) — форма даунстрима. Апстрим её не
  примет без нового YAML и спросит, почему это не часть `smp2p`/`remoteproc`;
- код помечен как порт даунстрима с копирайтом Linux Foundation
  (`0013-…:42-50`). GPL-2.0 допускает перенос, копирайт нужно оставить.
  Ссылку на источник взять ту же, что у Acayan
  (`android.googlesource.com/kernel/msm/…/smp2p_sleepstate.c`);
- «бит 12 независимо от ячейки» (`0013-…:60`) — магия даунстрима, её надо
  объяснить или вынести в DT.
Лучше сначала написать Acayan и в linux-arm-msm: у SDM670 и SM6115 одна
задача. Можно предложить драйвер поверх его биндинга. Сопровождающие soc/qcom
— Bjorn Andersson, Konrad Dybcio.

### `0015` fastrpc: пробуждение по сообщению DSP

В mainline `fastrpc.c` нет wakeup source (master, `grep wakeup` пуст). Серия
Ekansh Gupta 2023–2024 «Add early wakeup support» про другое — опрос вместо
прерывания (https://lore.kernel.org/r/20231121112454.12764-2-quic_ekangupt@quicinc.com).
Жёсткое событие пробуждения на каждое сообщение
(`pm_wakeup_hard_event`, 500 мс) работает, но может вызвать возражения: оно
будит систему на любой ответ DSP, а не только на обратный вызов слушателя.
Подавать как RFC после того, как войдёт патч Qualcomm про прерванные вызовы
(см. `0016`), с данными из `docs/sleep.md` (тест C, 27 коротких
пробуждений).

## Ядро: требует переработки

### Тач NT36523W (`0001`, `0002`, `0005`, `0008`)

В mainline есть только I2C-драйвер `novatek-nvt-ts.c` для NT11205 и
NT36672A (`novatek,nvt-ts.yaml`, master, строки 18-19), SPI и
загрузки прошивки с хоста в нём нет. Попытки влить общий NT36xxx:
- AngeloGioacchino Del Regno, v9, 2020:
  https://lore.kernel.org/r/20201028221302.66583-3-kholk11@gmail.com;
- Konrad Dybcio, v10, 2023:
  https://lore.kernel.org/r/20230808-topic-nt36xxx-v10-2-dd135dfa0b5e@linaro.org;
- George Chan, RFC/RFT SPI, 2024, с panel follower и загрузкой прошивки:
  https://lore.kernel.org/r/20241015-nt36xxx-v1-0-3919d0bffee6@gmail.com.
Ни одна не влита. Наш `0001` — вендорский драйвер Novatek/Xiaomi из форка
guf296 (`0001-…:1-7`), и как есть его не примут:
- нет SPDX и Signed-off-by автора форка. Лицензия GPL-2.0-or-later с
  копирайтом «Novatek, Inc.» и «XiaoMi, Inc.» позволяет перенос по DCO (b)
  (`submitting-patches.rst:418`), копирайты нужно сохранить;
- `compatible = "novatek,NVT-ts-spi"` с заглавными буквами
  (`0001-…:2114`; `kernel/sm6115-lenovo-j606l.dts:147`) и
  `lenovo,tb321fu-nt36523n-spi`. Биндинга нет;
- адреса регистров в DT: `novatek,event-buf-addr`, `novatek,swrst-n8-addr`,
  `novatek,spi-rd-fast-addr` (`kernel/sm6115-lenovo-j606l.dts:160-162`).
  Сопровождающие DT отвечают, что это данные чипа для таблицы `match_data`;
- `#if NVT_TOUCH_ESD_PROTECT`, `procfs`, «android16 range» и прочий
  вендорский код (`0001-…:144-188`);
- известные ошибки времени жизни: oops при unbind (#29) и при уходе панели
  (#24).
Путь вперёд: взять серию George Chan (ядро и SPI отдельно, panel follower)
или v10 Konrad за основу, добавить вариант NT36523W (адрес буфера событий,
12-битные координаты из `0002`) как данные чипа и написать Dmitry Torokhov
в linux-input (`MAINTAINERS:12705`). Объём большой. Перед этим стоит
узнать в linux-arm-msm, не работает ли кто-то над тачем J606F/elish
(та же NT36523).

Двойной тап (`0008`). Свойство `novatek,double-tap-wake` заменяется
стандартным `wakeup-source`. Свойство панели `novatek,tddi-touch-wake`
(`:436`), при котором `unprepare` не снимает питание, затрагивает DRM: его
придётся обсуждать с Neil Armstrong и Jianhua Lu в dri-devel. Возможно,
нужен общий механизм TDDI в `drm_panel_follower`.

### AW88258 (`0006`)

В mainline есть драйвер `aw88261`, но он принимает только chip id 0x2113
(`aw88261.c`, master, строки 1281-1288). У AW88258 id 0x1852
(`0006-…:38`). Val Packett прислала «ASoC: codecs: aw88261: use correct
registers for AW88258» (20 апреля 2026, не влит),
https://lore.kernel.org/r/20260420213250.215465-4-val@packett.cool. Значит,
сообщество видит AW88258 вариантом `aw88261`. Сам `aw88261` уже разбирает ACF
через общую библиотеку `aw88395_lib` (`aw88261.c` 7.1, строки 1050, 1104,
1123), а наш драйвер разбирает ACF сам. Отдельный `aw88258.c` Mark Brown,
скорее всего, не примет. Нужно:
- добавить `awinic,aw88258` в `awinic,aw88395.yaml` (сейчас там aw88081,
  aw88083, aw88166, aw88261, aw88395, aw88399 — строки 20-25);
- вместо своего `awinic,channel` (`kernel/sm6115-lenovo-j606l.dts:195`) взять
  существующее `awinic,audio-channel` (`awinic,aw88395.yaml:42`);
- научить `aw88261` id 0x1852 и регистрам AW88258 вместе с патчем Val
  Packett или поверх него: у неё не было железа, у нас есть;
- перевод четырёхслотового TDM из ACF в двухслотовый I2S
  (`0006-…:154-162`) делать через `set_tdm_slot`, а не правкой значений
  ACF;
- если код взят из GPL-драйвера Awinic в исходниках Lenovo, сохранить
  копирайт Awinic (`0006-…:14-15`).
Файл `awinic/aw882xx_acf.bin` — профиль Lenovo, в linux-firmware его нет.
Пользователь берёт его из своего `vendor_b` (`rootfs/haltia-firmware:27-28`).
Получатели: Liam Girdwood, Mark Brown, linux-sound (`MAINTAINERS:25042`). Ещё
стоит написать Val Packett и Vladyslav Tymoshchuk: он ведёт свежие правки
`aw88261`, https://lore.kernel.org/r/20261016120000.aw88261-trigger-v2-1-tvlad744@gmail.com.

### ES7210 и захват SEC_MI2S (`0007`)

ES7210 в mainline нет (`sound/soc/codecs/es7210.c` в master — 404; patchwork
пусто). Но на J606L ES7210 не несёт микрофоны: они идут через DBMD8 на линии
данных 1, а ES7210 сидит на линии 0 (issue #21; `kernel/sm6115-lenovo-j606l.dts:258-265`).
Драйвер нужен только как кодек для DAI-связи и как DAPM-виджет. Это слабый
довод для нового драйвера, а последовательности регистров Everest
(`0007-…:57-58`) без описания почти не прочесть. Предлагать только
вместе с драйвером DBMD8 или отказаться.

Изменение `sm8250.c` (`0007`) задаёт для `SECONDARY_MI2S_TX` 16 кГц, S24 и
внешний битовый такт для всех плат с этим машинным драйвером, в том числе для
`qcom,qrb4210-rb2-sndcard` (`sound/soc/qcom/sm8250.c` 7.1, строка 195). Так
нельзя. Нужен свой `compatible` карты (например `lenovo,j606l-sndcard`) с
данными платы или формат и такты из DT (`dai-format`, `bitclock-master` в
DAI-связи). Сопровождающий — Srinivas Kandagatla (`MAINTAINERS:21632`). DT
макросов LPASS и WCD937x у нас идёт по серии Alexey Klimov для RB2. Она не
влита, последняя версия — v3 от мая 2025,
https://lore.kernel.org/r/20250522-rb2_audio_v3-v3-7-9eeb08cab9dc@linaro.org.
Звук J606L в апстриме зависит от неё.

### DBMD8

Драйвера ядра нет. Загрузчик в userspace работает через spidev
(`rootfs/haltia-dbmd8:10-14`), а spidev привязан чужим `compatible`
`rohm,dh2228fv` (`kernel/sm6115-lenovo-j606l.dts:445`). Это известный приём,
и в апстрим его не примут. Вендорский `dbmdx` в исходниках Lenovo — около
32 000 строк (issue #21). Префикса `dspg` в `vendor-prefixes.yaml` нет.
Апстрим-путь: маленький кодек ASoC `dspg,dbmd8` (сброс, загрузка
предзагрузчика и прошивки по SPI, регистры usecase, старт и стоп) плюс
биндинг. Прошивки `dbmd8_va_fw.bin` и ASRP — Lenovo/DSPG, в linux-firmware их
не будет. Объём самый большой в списке.

### DTS платы `sm6115-lenovo-j606l.dts`

Mainline J606F есть, с 2023 года (дисплей, GPU), и его поддерживает Konrad
Dybcio
(https://lore.kernel.org/r/20230620-topic-gpu_tablet_disp-v2-2-0538ea1beb0b@linaro.org).
Его же «Add some peripherals» (2024) осталось в «changes-requested»:
https://lore.kernel.org/r/20240212-topic-j606f_periphs-v1-1-5dcacd483e28@linaro.org.
Препятствия:
- наш файл включает `.dts` J606F (`kernel/sm6115-lenovo-j606l.dts:7`). В
  апстриме общее выносят в `sm6115-lenovo-j606.dtsi`, а `j606f.dts` и
  `j606l.dts` делают тонкими;
- платы различаются: у J606F по Konrad контроллер USB-C RT1715, у J606L
  `fcs,fusb302` (`:230`);
- `lenovo,j606l` добавить в `Documentation/devicetree/bindings/arm/qcom.yaml`
  рядом с `lenovo,j606f` (строка 1003 в 7.1). `qcom,msm-id` и
  `qcom,board-id` устарели, но для `qcom,sm6115` разрешены (там же, строки
  1205-1300);
- в DTS можно отправлять только узлы с биндингами: тач, AW88258, ES7210,
  SGM37604A, sleepstate, DBMD8 ждут своих драйверов. Начать с того, что
  описано уже сейчас: питание, UFS, USB, Wi-Fi, Bluetooth WCN3990, MM8013,
  fusb302, дисплей, GPU, remoteproc, MPM;
- пути прошивок `qcom/sm6115/LENOVO/J606L/*.mdt` (`:110-130`). В mainline
  J606F стоят `.mbn` (`sm6115p-lenovo-j606f.dts`, master, строки 73-143).
  Апстрим ждёт `.mbn` по соглашению linux-firmware; `.mdt` у нас из-за
  копирования разбитых образов со стока.
Получатели: Bjorn Andersson, Konrad Dybcio, linux-arm-msm, devicetree
(`get_maintainer.pl -f arch/arm64/boot/dts/qcom/sm6115p-lenovo-j606f.dts`).

### Мелкие правки, которые лучше сделать в ядре

- `82-j606l-battery.rules`: MM8013 не шлёт событие при смене источника
  питания, и udev дёргает `uevent` вручную. Нормальное исправление в ядре —
  `power_supply_changed` или связь `power-supplies` с TCPM в DT. Драйвер
  ведёт Konrad Dybcio (`MAINTAINERS:17906`).
- `83-j606l-bt-wake.rules`: RX UART будил систему сразу. Правильное место —
  пины сна или `wakeup-source` в DT, а не udev.
- OTG (issue #17, `artifacts/2026-10-28-otg/dts-otg.diff`): fusb302 не видит
  `VBUSOK`, пока PMI632 даёт VBUS. Пока причина не найдена, в апстрим нечего
  нести, кроме отчёта в linux-usb.

## Дистрибутив и userspace

### postmarketOS (Nura) pmaports

Пакетов `device-lenovo-j606f` и `device-lenovo-j606l` нет: в `device/` 486
каталогов, совпадений по «j606», «sm6115», «tb-» нет (дерево через API
gitlab.postmarketos.org, ветка `main`). Есть ядро
`linux-nura-qcom-sm61x5` (7.2.3, «Close to mainline linux kernel for
Qualcomm Snapdragon SM61x5», сопровождающий Barnabas Czeman). Его источник —
https://codeberg.org/sm61x5-mainline/linux, ветка `sm61x5/7.2.3`. Им уже
пользуется `device-oneplus-billie2` (SM4250). В этом форке
`sm6115p-lenovo-j606f.dts` совпадает с mainline, драйверов ES7210 и SGM37604A
нет. Похоже, проект переименован в Nura: вики `wiki.nura.eco`, пакеты
`linux-nura-*`.

Путь: патчи ядра, которые ещё не в mainline, предложить в
`sm61x5-mainline/linux` (Codeberg, pull request), потом прислать MR в
pmaports с `device-lenovo-j606l` в `device/testing`.
- Стиль коммитов — `COMMITSTYLE.md` pmaports (по образцу Alpine aports).
- Правила категорий — `docs/packaging/device-categorization.md`. Для
  community нужны ядро «close to mainline» и проход `pmbootstrap kconfig
  check --community`.
- Прошивки — `docs/packaging/firmware-packages.md`. Порядок: linux-firmware,
  потом пакет `firmware-*`, и только потом раздел на устройстве через
  `msm-firmware-loader`. Для J606L возможен только третий вариант (см.
  linux-firmware), и `rootfs/haltia-firmware` надо заменить на
  `msm-firmware-loader`.
- `rootfs/haltia-rtc` повторяет пакет `swclock-offset` («Keep system time at
  an offset to a non-writable RTC», `main/swclock-offset`): в пакете
  устройства взять его.
- Матрица ориентации из `81-j606l-sensors.rules` и `hexagonrpcd.confd` ложатся
  в пакет устройства. В hwdb systemd записи `60-sensor.hwdb` привязаны к
  ACPI/DMI, а не к DT
  (https://github.com/systemd/systemd/blob/main/hwdb.d/60-sensor.hwdb, строки
  7-8).

### alsa-ucm-conf

Конфигурации для SM4250/QRB4210 нет: в `ucm2/Qualcomm/` есть sm8250,
sc8280xp, qcm6490 и другие, `sm4250` и `qrb4210` нет; в `ucm2/conf.d/`
есть только `sm8250` (дерево https://github.com/alsa-project/alsa-ucm-conf,
ветка master). Машинный драйвер для `qcom,qrb4210-rb2-sndcard` называет
карту `sm4250` (`sound/soc/qcom/sm8250.c` 7.1, строка 195). Поэтому файл
ложится в `ucm2/conf.d/sm4250/Lenovo-TB-J606L.conf`, а HiFi — в
`ucm2/Qualcomm/sm4250/…`. Наш путь `/Lenovo/TB-J606L/HiFi.conf`
(`rootfs/ucm/Lenovo-TB-J606L.conf:4`) нужно перенести; образец —
`ucm2/conf.d/sm8250/Qualcomm-RB5-WSA8815-Speakers-DMIC0.conf`. Подача: PR на
GitHub с выводом `alsa-info.sh` для валидатора (README репозитория, раздел
Validation). Отправлять после того, как в ядро войдут драйверы и имена
контролов (`PRI_MI2S_RX Audio Mixer MultiMedia1`, `MultiMedia2 Mixer
SEC_MI2S_TX` из `rootfs/ucm/HiFi.conf:7-12`). Иначе UCM будет описывать ядро,
которого нет в апстриме.

### iio-sensor-proxy

Поддержка libssc влита в феврале 2026 (MR 381,
https://gitlab.freedesktop.org/hadess/iio-sensor-proxy/-/merge_requests/381).
Upstream-правило ставит для `fastrpc-adsp*` только `ssc-light ssc-compass`
(`data/80-iio-sensor-proxy.rules`, строки 21-25). Наш `ssc-accel
ssc-proximity` (`rootfs/81-j606l-sensors.rules:5`) ровно то, что добавляет
открытый MR 409 «data: update libssc udev rules»,
https://gitlab.freedesktop.org/hadess/iio-sensor-proxy/-/merge_requests/409.
Полезно отписаться в MR 409, что на SM6115 (J606L, ADSP) акселерометр и
близость работают. Ошибку с поворотом после пробуждения («claim до
`HasAccelerometer = true`», `docs/sleep.md`) лечит открытый MR 414
«Broadcast sensor capability changes to all clients»,
https://gitlab.freedesktop.org/hadess/iio-sensor-proxy/-/merge_requests/414.
Его тоже можно проверить и подтвердить.

### hexagonrpc

https://github.com/linux-msm/hexagonrpc содержит только службы systemd и
Android rc (`data/`: `hexagonrpcd-adsp-sensorspd.service.in`, `.rc`).
Устройство-специфичного там ничего нет: каталог
`/usr/share/qcom/sm6115/Lenovo/J606L` (`rootfs/hexagonrpcd.confd`) — забота
пакета устройства. Возможный вклад — службы OpenRC, если их нет в пакете
Alpine. И отчёт о #18 (падение SoC при раннем старте обоих PD), когда
причина будет найдена.

### linux-firmware — нельзя

В `WHENCE` нет ничего для `qcom/sm6115/LENOVO/…`. Для QRB4210 лежат образы,
подписанные Qualcomm (`qcom/qrb4210/adsp.mbn`, `cdsp.mbn`, `modem.mbn`; WHENCE
строки 7281-7293). OEM-прошивки Lenovo в linux-firmware попадают, только когда
Lenovo даёт лицензию, как для ноутбуков X13s, Slim 7x и других
(`qcom/sc8280xp/LENOVO/21BX/…`, строки 7184-7186, 7325-7327)
(https://gitlab.com/kernel-firmware/linux-firmware/-/raw/main/WHENCE). Образы
J606L (`adsp`, `cdsp`, `modem`, `a610_zap`), прошивка тача
`novatek_ts_fw.bin`, профиль `aw882xx_acf.bin` и прошивки DBMD8 подписаны или
созданы Lenovo, и распространять их нельзя. Они остаются на устройстве
(`kernel/README.md:73-75`). Отправить их в linux-firmware может только
Lenovo.

## Что не уходит в апстрим как есть

| Что | Почему |
|---|---|
| `0001` целиком | Вендорский код без SPDX и Signed-off-by автора, адреса регистров в DT, `compatible` с заглавными буквами, ошибки времени жизни (#24, #29) |
| `novatek,tddi-touch-wake` в панели (`0008`) | Политика питания панели ради тача. Нужно согласие DRM |
| `sm8250.c` в `0007` | 16 кГц и внешний такт для всех плат на этом драйвере |
| `0012` | Меняет тайминги CSIPHY для всех SoC |
| `0016` | Есть более полное исправление Qualcomm v3 |
| `0017` | Исправлено иначе в mainline |
| `0009` | Уже в v7.2 |
| `rohm,dh2228fv` для DBMD8 | Чужой `compatible` ради spidev |
| `#include "sm6115p-lenovo-j606f.dts"` | В апстриме — общий `.dtsi` |
| `haltia-firmware`, `haltia-rtc` | Есть `msm-firmware-loader` и `swclock-offset` |

## Рекомендуемый порядок

Сначала то, что дёшево и полезно другим, потом то, что открывает дорогу
большим работам.

1. **Отчёты `Tested-by`** к чужим сериям: fastrpc v3 (заменяет `0016`) и
   `devm_drm_panel_add` для nt36523 (заменяет `0014`). Один день работы на
   планшете, ничего своего не нужно, и патчи `0014`/`0016` уходят из порта.
2. **Переход ядра на ≥7.2** (лучше на `sm61x5-mainline` или mainline, а не на
   форк MT6589): уходит `0009`, после бэкпорта — `0017`.
3. **`0011` ov8856** — первый свой патч: маленький, `Fixes:`, понятный сбой.
   На нём отработать `b4`, `Assisted-by` и подпись.
4. **`0004` dwc3-qcom** (оба файла) — маленький и полезный всем SM6115/QCM2290
   в s2idle.
5. **MPM в `sm6115.dtsi`** — после исправления psci-cpuidle. Даёт сон всем
   платам SM6115.
6. **Биндинг и DTS J606L, минимальный** — общий `sm6115-lenovo-j606.dtsi` с
   J606F, только узлы с биндингами. Ставит плату в mainline и даёт место для
   следующих узлов.
7. **`0003` SGM37604A** с биндингом. Выяснить, стоит ли он на J606F.
8. **`0010` CAMSS SM6115**: биндинг, драйвер, узлы `sm6115.dtsi`. `0012` —
   отдельным RFC.
9. **AW88258 как вариант `aw88261`** вместе с Val Packett. Звук целиком ждёт
   серию LPASS/WCD937x Alexey Klimov и свою карту вместо правки `sm8250.c`.
10. **`0013` sleepstate и `0015` fastrpc-wake** — RFC в linux-arm-msm
    совместно с Richard Acayan.
11. **pmaports** `device-lenovo-j606l` в `testing` на ядре sm61x5, с
    `msm-firmware-loader` и `swclock-offset`; UCM в alsa-ucm-conf, когда звук
    будет в ядре.
12. **Тач NT36523W и DBMD8** — самые большие. Тач — поверх серии George Chan
    или Konrad после разговора в linux-input. DBMD8 — новый маленький кодек
    ASoC.
