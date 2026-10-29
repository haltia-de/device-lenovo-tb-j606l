import copy
import struct
import unittest

import package


class PackageTests(unittest.TestCase):
    def test_newc_contains_only_new_init_and_ram_console(self):
        raw=package.newc(b'new-static-init\x00');cursor=0;entries={}
        while True:
            self.assertEqual(raw[cursor:cursor+6],b'070701')
            fields=[int(raw[cursor+6+i*8:cursor+14+i*8],16) for i in range(13)]
            cursor+=110
            name=raw[cursor:cursor+fields[11]-1].decode();cursor+=fields[11];cursor=(cursor+3)&~3
            data=raw[cursor:cursor+fields[6]];cursor+=fields[6];cursor=(cursor+3)&~3
            self.assertEqual((fields[2],fields[3],fields[5]),(0,0,0))
            entries[name]=(fields,data)
            if name=='TRAILER!!!':break
        self.assertEqual(set(entries),{'.','dev','dev/console','init','TRAILER!!!'})
        self.assertEqual(entries['init'][1],b'new-static-init\x00')
        self.assertEqual(entries['dev/console'][0][9:11],[5,1])
        self.assertEqual(raw,package.newc(b'new-static-init\x00'))

    def test_exact_stock_security_word_and_addresses_are_enforced(self):
        stock=package.STOCK_CONTROL['header']
        self.assertEqual(stock['os_version_word'],0x16000177)
        package.check_header(stock,stock)
        for key in ('os_version_word','kernel_addr','ramdisk_addr','dtb_addr','page_size','header_version'):
            candidate=copy.copy(stock);candidate[key]+=1
            with self.subTest(key=key),self.assertRaises(ValueError):package.check_header(candidate,stock)


if __name__=='__main__':unittest.main()
