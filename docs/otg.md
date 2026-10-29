# USB OTG на TB-J606L

Проба 28 октября 2026, issue #17. В дерево устройств не вошла: питание на
разъём приходит, но порт его не видит.

## Что пробовали

Порт USB-C ведёт fusb302 (TCPM, I2C `2-0022`). В стоке VBUS для хоста даёт
буст зарядника PMI632 (`smb5-vbus`). Изменения DTS:

```dts
#include "pmi632.dtsi"

/* в узле fusb302 */
vbus-supply = <&pmi632_vbus>;
connector {
	power-role = "dual";
	try-power-role = "sink";
	data-role = "dual";
	source-pdos = <PDO_FIXED(5000, 900, PDO_FIXED_USB_COMM)>;
	/* + ports/port@0/endpoint fusb302_hs -> usb_dwc3_hs */
};

&pmi632_vbus {
	regulator-min-microamp = <500000>;
	regulator-max-microamp = <1000000>;
	status = "okay";
};

&usb_dwc3 {
	dr_mode = "otg";
	usb-role-switch;
};

&usb_dwc3_hs {
	remote-endpoint = <&fusb302_hs>;
};
```

## Что работает

- PMI632 появляется на SPMI, порт становится двухролевым,
  `4e00000.usb-role-switch` переводит dwc3 в хост, xhci поднимается.
- С USB-C доком (без своего питания) TCPM видит `cc2=Rd`, идёт
  `SRC_ATTACH_WAIT -> SRC_ATTACHED` и включает `usb_vbus`. АЦП PMI632 читает
  на входе USB **5,006 В**, пока регулятор включён: буст работает и доходит
  до разъёма.

## Что не работает

- fusb302 не сообщает `VBUSOK`, пока планшет сам даёт питание. TCPM через
  `PD_T_PS_SOURCE_ON` (480 мс) уходит в `SRC_UNATTACHED` и повторяет
  каждые ~1,3 с. Док так и не появляется.
- GPIO 38 TLMM (`usb_vbus` стокового `dock_pogo`) в единицу — без
  изменений.
- Тестовый fusb302, который считал VBUS присутствующим, раз он его сам
  включил, после переподключения дальше `SRC_ATTACH_WAIT` не прошёл.
  Дальше не разбирали.

## Побочное

С описанным PMI632 его GPIO-контроллеры пробуются раньше TLMM, и TLMM
перестаёт быть `gpiochip0`. `haltia-dbmd8` с тех пор ищет его по метке
`500000.pinctrl` (57b79f7).

Прямое чтение регистров fusb302 через `i2cget` на той же шине во время
переключений подвесило Wi-Fi-связь; не повторять.

## Что дальше

- Проверить, подключён ли вывод VBUS fusb302 на J606L вообще.
- Или брать признак VBUS не от fusb302, а от PMI632 (вход USB, зарядник).
