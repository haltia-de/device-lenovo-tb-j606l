# Первый диагностический тест: draft для review, не разрешение исполнения

Linux ещё не загружен. Ни одна описанная запись/переключение здесь не выполнена.
Все действия с устройством требуют отдельного exact root review/GO и одного
координатора под shared lock. Повтор при неуспехе не выполняется автоматически.

Актуальный кандидат архитектора и его границы описаны в
[плане первой RAM-загрузки](https://github.com/haltia-de/haltia/blob/main/docs/plans/j606l-first-ram-boot.md):
downloaded boot при выбранном A, подготовка только DTBO A и явный возврат B.
Он отдельно проверяется. Приведённый ниже вариант постоянного A bundle —
рассмотренная альтернатива; его дополнительные записи/readback не являются
автоматически обязательными условиями RAM-кандидата.

## Свежая измеренная отправная точка

Read-only fastboot preflight25 октября завершился с возвратом прежнего Android B
и boot_completed1, всеми клиентами stopped/reaped. Capture в bootloader:
current-slot B, slot-count2, is-userspace=false, unlocked=true, secure=true.
Secure и unlocked — отдельные observations. A successful=true, unbootable=false,
retry7; B successful=true, unbootable=false, retry6. Это значения в capture point;
следующая загрузка Android могла штатно изменить metadata. Для будущего boot
нужны новые flags в review-gated transaction, а не перенос этих значений из памяти.

Размеры fastboot согласуются с принятыми backup/GPT: boot и recovery обоих слотов
100663296 B, dtbo25165824 B, vbmeta/vbmeta_system65536 B; modemst1/2/fsg2097152 B,
fsc131072 B, persist33554432 B, misc1048576 B, devinfo4096 B.
Has-slot только boot=true; остальные11 неизвестны, а не absent/unpartitioned.
Наличие конкретных `_a/_b` подтверждено независимо обеими GPT и backup addresses.

Fastboot rc0 недостаточен: один has-slot reply содержал FAILED при rc0. Будущий
controller обязан отвергать FAILED/error независимо от rc и требовать ожидаемый
положительный protocol result каждого boot/flash/set_active/reboot этапа.
ACK не заменяет readback и runtime observer. Возврат B preflight доказан самим
Android observer, а не только кодом возврата команды reboot.

## Что сообщает reference, и чего он не доказывает

Закреплённый [Qualcomm/SHIFT reference7d391d8b](https://github.com/SHIFTPHONES/android_bootable_bootloader_edk2/tree/7d391d8b1059ed48259728cab004ca6f16ee3de2)
не является исходником Lenovo production. В нём downloaded CmdBoot добавляет
RAM boot image, очищает unbootable активного слота и запускает image auth;
то есть RAM download не гарантирует отсутствие изменений active-slot metadata.
VB2 при downloaded boot пропускает загрузку BOOT из раздела, но запрашивает DTBO
безусловно. Stock active-slot DTBO нельзя считать автоматически обойдённым.

LocateDeviceTree.c GetSocDtb меняет DtboNeed на false лишь при CheckAllBitsSet.
Header ALL_BITS_SET требует SOC_MATCH, VARIANT_MATCH, SUBTYPE_EXACT_MATCH,
FOUNDRYID_EXACT_MATCH, exact PMIC model bits IDX0..F и SOFTSKU_EXACT_MATCH.
Это больше, чем msm444 и board34/3. SoC version, variant major/minor, DDR и PMIC
revision также участвуют в поиске/ranking, но не заменяют перечисленные exact bits.
Новый DTB содержит msm444/0x10000 и board34/3, но не qcom,pmic-id/pmic-id-size,
softsku не измерен, encoded foundry0 не проверен по production Board interface.
Без PMIC properties reference не устанавливает требуемые exact PMIC bits.
Следовательно, exact-match DTBO skip для этого пакета **не доказан**.

Board34/3 — metadata выбранной штатной LTE DTBO8, live sysfs subtype0 — другое
измерение. Ни одно не объявляется известным production BoardPlatformSubType
для matching. Патч автора J606F2022 требовал изменения boot/dtbo/recovery;
он не доказывает текущую LTE логику. Пустые файлы из исторического рецепта
не предлагаются как готовые J606L artifacts.

## Вариант downloaded boot при active B

Пока не выбран для первого теста: возможны изменения metadata B, загрузка
stock DTBO поверх mainline DTB и recovery selection. Отсутствие записи payload B
не устраняет эти эффекты. Для такого варианта потребовались бы отдельное
доказательство Lenovo download/DTBO matching и проверенный возврат B; сейчас их нет.
Слепой `fastboot boot` с активным B в предложенный GO не входит.

## Рассмотренная альтернатива: постоянный A bundle

Это отдельная последовательность для дальнейшего сравнения, но набор
A и controller ещё не приняты. Согласованный inactive-A набор с обычным boot
мог бы не полагаться на downloaded-boot bypass, однако требует дополнительных
образов и записей, перечисленных ниже.

1. Проверить immutable backup manifest и вторую физическую копию, выбранные
   binary hashes/header/DTB/config и protocol-aware controller. Проверить exact
   serial+port, тот же AndroidB/boot_completed, затем bootloader mode и unlock,
   currentB, A/B flags и размеры. До этого никаких записей/slot changes.
2. Пока B active, подготовить отдельно reviewed boot_a с новым диагностическим
   payload, dtbo_a с валидным minimal no-op J606L overlay и recovery_a с тем же
   диагностическим payload на случай recovery selection. Полные partition-sized
   buffers должны исключать старый AVB/footer/tail. Valid no-op overlay нужно
   проверить parser+fdtoverlay и на reference selection; acceptance Lenovo неизвестна.
   Эти дополнительные A artifacts пока не построены. Никаких bare alias/all-slots.
3. Отдельно решить AVB/vbmeta_a: unlocked не доказывает bypass. Проверить штатные
   rollback indices/locations обоих слотов; если временный A vbmeta необходим,
   он требует отдельного review, сохранения индексов без advance и согласованной
   AVB политики. Не менять vbmeta B, root trust, security patch или userdata/super.
   Пока это не решено, записывать/загружать A нельзя.
4. После exact GO записать только именованные A payload partitions, требуя
   положительного protocol результата и отсутствия FAILED/error. До выбора A
   выполнить отдельно reviewed numeric readback этих же A областей и сверку
   размеров/полных SHA. Flash ACK не считается проверкой байтов. Вернуться AndroidB,
   проверить binding/boot_completed, затем отдельный согласованный boot этап.
5. При одном дальнейшем boot GO — fresh bound bootloader, ещё раз проверить B
   recovery flags, один set_active A с protocol success и проверкой flags, один
   normal reboot. A/B selection меняет общую GPT metadata, включая active flags B;
   это надо явно включить в review, а не называть операцию полностью B-read-only.
   Payload B остаётся неизменным, B должен оставаться successful/bootable.
6. Host observer120s ждёт новый ACM на точном порту/artifact build ID и принимает
   только Linux+aarch64+PID1+RAM-root+полный CRC-kmsg. Нет shell/persistent writes,
   MDSS/rproc/storage init. PID1 около90s один раз запрашивает bootloader.
   Это ещё не проверено на устройстве; panic0 не создаёт automatic reboot loop A.
7. При фактическом свежем fastboot — единственный явный set_active B от host
   coordinator, protocol success без FAILED/error, currentB и сохранённые B
   successful/unbootable flags. Затем один normal reboot, две bound проверки
   прежнего model/build/B/boot_completed. Только это завершает тест.

Если kernel/USB proof не получен или появился bootloader без proof, результат
Linux — FAIL, но bounded возврат B остаётся обязанностью координатора. Никакого
повторного Linux boot. При hang/early panic после истечения deadline сначала
подтвердить остановку/reap всех host clients; root координирует один физический
вход в fastboot, затем явный возврат B. Если fastboot не появился, не отправлять
reset/EDL/programmer/flash автоматически: остановиться с приватным evidence и
эскалировать root. Резерв B и счётчик retry сами по себе не доказывают fallback.

До hardware review остаются: готовый A bundle/AVB policy, readback и slot-safe
protocol-aware coordinator, фиксированные physical fallback действия и точный
auth с boundary на каждый phase. Этот документ не снимает эти ограничения.

Одна host reboot-команда не гарантирует единственную внутреннюю попытку bootloader до PID1. При раннем сбое bounded stop обеспечивается deadline и заранее согласованным физическим входом в fastboot, а не предположением о семи retries. Точный Lenovo matching/AVB/recovery путь остаётся условием review.
