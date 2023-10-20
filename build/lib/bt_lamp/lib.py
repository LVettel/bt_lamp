import os
import sys
import struct
from time import sleep
from logging import basicConfig, getLogger, getLevelName, INFO, DEBUG, WARN, WARNING, ERROR

from bleson.logger import set_level
from bleson import get_provider, Advertiser, Advertisement, UUID16, LE_LIMITED_DISCOVERABLE
from bleson.providers.linux.linux_adapter import BluetoothHCIAdapter
from bleson.providers.linux.constants import HCI_COMMAND_PKT

from bleson.core.hci.constants import GAP_FLAGS, GAP_UUID_16BIT_COMPLETE, LE_SET_ADVERTISING_PARAMETERS_CMD
from bleson.core.hci.types import HCIPayload
from bleson.core.hci.type_converters import AdvertisingDataConverters

from crcmod.predefined import Crc

LOGGER_NAME = "BtLamp"
LOG_FORMAT= '%(asctime)s %(levelname)6s - %(filename)24s:%(lineno)3s - %(funcName)24s(): %(message)s'
basicConfig(level=INFO, format=LOG_FORMAT)
log = getLogger(LOGGER_NAME)

# Правлю ошибку в методе HCIPayload.add_item
class MyHCIPayload(HCIPayload):

    def add_item(self, tag, value):
        """
        :param tag:    HCI packet type
        :param value:  array of byte-like data or homogeneous array of 'ValueObjects'
        :return:       self
        """
        from bleson import ValueObject
        log.debug("tag={} len={} data={} data={}".format(tag, len(value), type(value), value))

        if all(isinstance(item, ValueObject) for item in value):
            new_len=0
            for vo in value:
                log.debug("VO len={} data={} bytes={}".format(len(vo), vo, bytes(vo)))
                new_len += len(vo)

            new_data = self.data + struct.pack("<BB", 1 + new_len, tag)
            
            for vo in value:
                new_data = new_data + bytes(vo)
        else:
            new_data = self.data + struct.pack("<BB", 1 + len(value), tag) + bytes(value)

        log.debug("New len={} data={}".format(len(new_data), new_data))

        if len(new_data) <= 31:
            self.data = new_data
            self.tags[tag] = value
        else:
            raise IndexError("Supplied advertising data too long (%d bytes total)", len(new_data))
        return self

class BtPackage:
    def __init__(self, name, command, arg0, arg1, log_level):
        self._name = name
        self._command = command
        self._arg0 = arg0
        self._arg1 = arg1
        self._log_level = log_level
    
    def get_data(self):
        message = bytearray(25)

        # постоянный заголовок
        message[0] = 0x71
        message[1] = 0x0F
        message[2] = 0x55
        message[3] = 0xAA
        message[4] = 0x98
        message[5] = 0x43
        message[6] = 0xAF
        message[7] = 0x0B
        message[8] = 0x46
        message[9] = 0x46
        message[10] = 0x46
        
        # Команда        
        message[11] = self._command
        
        # Идентификатор лампы
        lamp_id = BtPackage.get_lamp_id(self._name)
        message[12] = lamp_id[0]
        message[13] = lamp_id[1]
        
        # Аргументы
        message[14] = self._arg0
        message[15] = self._arg1

        #Константа
        message[16] = 0x83
        
        # Случайное число (1 байт)
        message[17] = os.urandom(1)[0]

        # постоянный суффикс
        message[18] = 0x00
        message[19] = 0x00
        message[20] = 0x00
        message[21] = 0x00
        message[22] = 0x00

        # Контрольная сумма
        crc = self.get_crc(message[11:23]) 
        message[23] = crc[0]
        message[24] = crc[1]
        
        # print('[D] 1 msgBase=' + message.hex(' ', 1))

        # revers bits
        message = self.revers(message)
        # print('[D] 2 msgRev=' + message.hex(' ', 1))

        # bte whitening
        message = self.whitener(message)
        # print('[D] 2 msgWht=' + message.hex(' ', 1))

        # Формируем массив объектов UUID16
        result = []
        for idx, item in enumerate(message):
            if idx % 2 == 0:
                if (idx+1) < len(message): 
                    result.append(UUID16(message[idx:(idx+2)]))
                else:
                    result.append(UUID16(message[idx]))
        
        return result
    
    @staticmethod
    def get_lamp_id(lamp_name):
        crc_16 = Crc('crc-ccitt-false')
        crc_16.update(lamp_name.encode('utf-8'))
        return crc_16.crcValue.to_bytes(2, 'big')
    
    def get_crc(self, message):
        crc_16 = Crc('crc-ccitt-false')
        crc_16.update(message)
        return crc_16.crcValue.to_bytes(2, 'big')
    
    def revers(self, message: bytearray) -> bytearray:
        result = bytearray(len(message))
        for i, byte in enumerate(message):
            res_byte = 0
            for j in range(8):
                if (byte >> j) & 1: res_byte |= 1 << (7 - j)    
            result[i] = res_byte
        return result

    def whitener(self, message: bytearray) -> bytearray:
        lfsr = -7 # Первоночальная инициализация регистра сдвига
        result = bytearray(len(message))
        for i, byte in enumerate(message):
            # print ("IN:" + bin(byte) + " " + bin(lfsr))
            lfsr_res = 0 # Значение получаемое из регистра сдвига
            for _ in range(8):
                # Формируем байт маски из регистра сдвига
                lfsr_res = lfsr_res >> 1 # Сдвигаем регистр с результатом из регистра сдвига
                lfsr_res |= (lfsr & 64) << 1 # Берем седьмой бит из lfsr, перемещаем его в восьмую позицию и записываем в регистр результата
                
                # Сдвигаем регистр сдвига с обратной связью                
                lfsr <<= 1 # Сдвигаем влево
                b8 = (lfsr & 128) >> 7 # Восьмой бит
                b5 = (lfsr & 16) >> 4 # Пятый бит
                b5 = b5 ^ b8 # Новое значение пятого бита
                lfsr = (lfsr | b8) # Заполняем первый бит восьмым
                lfsr = (lfsr & -17) | (b5 << 4)  # Заполняем 5 бит
                lfsr &= 127 # Обнуляем восьмой бит
                # print ("    " + bin(lfsr_res) + " " + bin(lfsr))

            result[i] = byte ^ lfsr_res # Выполняем XOR операцию между исходным байтом и байтом, полученным из регистра сдвига
            # print ("OUT:" + bin(result[i]) + " " + bin(lfsr))
        return result

    def send(self):
        set_level(self._log_level)

        WAIT_TIME = 0.1

        # вызов get_provider().get_adapter() открывает адаптер, потом выключает а потом включает, много лишнего летит в контроллер, но возможно такой подход спасает от зависаний конроллера BT
        adapter = get_provider().get_adapter() 
        # Вместо этого только открываем, для тестировани, чтоб меньше логов анализировать
        # adapter = BluetoothHCIAdapter(0)
        # adapter.open()

        advertiser = Advertiser(adapter)
        advertisement = Advertisement()

        hci_payload = MyHCIPayload()
        hci_payload.add_item(GAP_FLAGS, [LE_LIMITED_DISCOVERABLE])

        hci_payload.add_item(GAP_UUID_16BIT_COMPLETE, self.get_data())

        advertisement.raw_data = hci_payload.data
                
        advertiser.advertisement = advertisement

        advertiser.start()
        sleep(WAIT_TIME)
        advertiser.stop()

class BtLamp:
    def __init__(self, name, log_level = INFO):
        self._name = name;
        self._levels = bytes(b'\x00\x1A\x33\x4C\x66\x7F\x99\xB2\xCC\xE5\xFF')
        self._log_level = log_level
        log.setLevel(log_level)

    def setup(self):
        lamp_id = BtPackage.get_lamp_id(self._name)
        arg0 = lamp_id[0]
        arg1 = lamp_id[1]
        command_code = 0x28
        self.send_package(command_code, arg0, arg1)
        log.info("Connecting to the lamp %s", self._name);

    def on(self):
        command_code = 0x10
        self.send_package(command_code)
        log.info("Turning the lamp %s on", self._name)

    def off(self):
        command_code = 0x11
        self.send_package(command_code)
        log.info("Turning the lamp %s off", self._name)

    def cold(self, level:int):
        self.check_level(level)
        command_code = 0x21
        self.send_package(command_code, level)
        log.info("Setting cold brightness to %i", level)

    def warm(self, level:int):
        self.check_level(level)
        command_code = 0x21
        self.send_package(command_code, 0x00, level)
        log.info("Setting warm brightness to %i", level)

    def dual(self, level:int):
        self.check_level(level)
        command_code = 0x21
        self.send_package(command_code, level, level)
        log.info("Setting dual brightness to %i", level)

    def send_package(self, command_code, arg0 = 0x00, arg1 = 0x00):
        package = BtPackage(self._name, command_code, arg0, arg1, self._log_level)
        package.send()

    def check_level(self, level):
        if (level < 1) or (level > 10):
            raise Exception("The level should be between 1 and 10")

if __name__ == "__main__":
    if (len(sys.argv) < 3):
        print("Use: python bt_lamp command lamp-name [level] [log-level]")
        print("   command: setup, on, off, cold, warm, dual")
        print("   lamp-name: name of the lamp")
        print("   level: brightness level, number from 1 to 10. Apply with command cold, warm or dual")
        print("   log-level: Logging level. Need INFO or DEBUG. Default value INFO")
    else:    
        command = sys.argv[1]
        name = sys.argv[2]
        if len(sys.argv) > 3:
            level = int(sys.argv[3])
        else:
            level = None

        if len(sys.argv) > 4:
            log_level = getLevelName(sys.argv[4])
        else:
            log_level = INFO

        lamp = BtLamp(name, log_level)
        if command == "setup":
            lamp.setup()
        elif command == "on":
            lamp.on()
        elif command == "off":
            lamp.off()
        elif command == "cold":
            lamp.cold(level)
        elif command == "warm":
            lamp.warm(level)
        elif command == "dual":
            lamp.dual(level)

        print("Command {0} executed on {1} with arg {2}".format(command, name, level))
