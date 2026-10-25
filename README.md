# Pertin Haltia для Lenovo Tab P11 (TB-J606L)

Слой устройства для Lenovo Tab P11 **TB-J606L** (Snapdragon 662, SM6115,
плата `bengal`). Оболочка и программы — общие, в [Haltia](https://github.com/haltia-de/haltia).
Решения порта — в [плане](https://github.com/haltia-de/haltia/blob/main/docs/plans/tab-p11.md).

> **Linux на планшете ещё не проверен.** Android B работает, критичный
> резерв проверен и сохранён на двух физических дисках. Новый
> [RAM/USB-образ J606L](diagnostics/ramdiag/README.md) собран и независимо
> воспроизведён побайтово. Готового образа повседневной Haltia пока нет.
> Проба загрузки требует отдельного проверенного сценария и контроллера.
> Прежний J606F one-shot выведен из обращения: ADR 0101.

*English summary: device support for the Lenovo Tab P11 TB-J606L. Critical
backups are verified; a reproducible J606L RAM diagnostic image is available
as source. Linux boot and permanent Android/Linux dual boot are not yet
verified. The retired J606F one-shot must not be reused.*

## Для какого устройства

Только **TB-J606L** (LTE, штатная сборка лабораторного экземпляра
`TB-J606L_S320317_230810_ROW`): Android 11, ядро производителя 4.19.
На TB-J606F (только Wi-Fi)
этот порт не проверялся. В основном ядре Linux есть дерево J606F
(`sm6115p-lenovo-j606f.dts`). Это соседняя модель, не эта.

## Что уже известно

Исходное досье 23 октября — в `docs/dossier.md`. Проверенные результаты
24–25 октября — в [профиле экземпляра](https://github.com/haltia-de/haltia/blob/main/docs/research/2026-10-24-j606l-stock-profile.md).

| Узел | Состояние |
|---|---|
| Загрузчик | открыт 23 октября 2026, состояние orange. `userdata` стёрт. В разделы образ не записывался. Android снова на слоте B |
| Слоты A/B | Android B проверен после прохода fastboot. В снимке загрузчика оба слота successful=true/unbootable=false; работа Android A этим не доказана. Linux планируется отдельно на A |
| Экран 1200×2000, 60 Гц, плотность 240 | в Android работает; физическая активная DSI-панель однозначно не установлена. Linux/MDSS пока не проверены |
| Касание Novatek | в Android подтверждена привязка NVT-ts к spi0.1; работа касания в Linux не проверена |
| Звук, зарядка, сон, Wi-Fi, поворот | в Android есть; на новом Linux J606L пока не проверены |

Повседневная планка, после которой модель может войти в линейку: экран,
касание, Wi-Fi, звук, сон, кнопка питания, поворот. LTE, камера, перо,
клавиатура и GPU в эту планку не входят.

## Копии разделов

17 критичных разделов и обе GPT шести экспонированных UFS LUN сохранены
двумя проходами. Полные размеры и SHA256 совпали; независимо проверены
GPT CRC/GUID/геометрия. Всего 58 файлов, копия проверена на другом
физическом диске ПК. Это критичный резерв, не полный firmware/userdata backup.
Задача [№ 3](https://github.com/haltia-de/device-lenovo-tb-j606l/issues/3)
закрыта с результатами. Исходное сравнение методов сохранено в
`docs/partition-backup.md`; оно не заменяет актуальный отчёт проверки.

## Диагностическая сборка

Исходники, закреплённые зависимости, команды чистой сборки и результаты
проверок находятся в [diagnostics/ramdiag](diagnostics/ramdiag/README.md).
В репозитории нет дампов разделов, приватных serial, firmware или
сгенерированных boot-образов. Первая аппаратная проба и постоянный dual
boot остаются следующими этапами плана.
