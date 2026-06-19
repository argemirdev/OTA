import board
import busio
import digitalio
import time

uart = busio.UART(board.GP4, board.GP5, baudrate=9600, bits=8, parity=None, stop=1, timeout=2)

de = digitalio.DigitalInOut(board.GP10)
de.direction = digitalio.Direction.OUTPUT
de.value = False

def crc16(data):
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc.to_bytes(2, 'little')

def read_pzem():
    while uart.in_waiting:
        uart.read(uart.in_waiting)

    pkt = bytearray([0x01, 0x04, 0x00, 0x00, 0x00, 0x0A])
    pkt += crc16(pkt)

    de.value = True
    time.sleep(0.02)
    uart.write(pkt)
    time.sleep(0.02)
    de.value = False

    tampon = bytearray()
    bitis = time.monotonic() + 2.0
    while time.monotonic() < bitis:
        if uart.in_waiting:
            chunk = uart.read(uart.in_waiting)
            if chunk:
                tampon += chunk
        if len(tampon) >= 26:
            break
        time.sleep(0.001)

    #print("RAW:", [hex(x) for x in tampon])

    for i in range(len(tampon)):
        if tampon[i] == 0x01 and i + 1 < len(tampon) and tampon[i+1] == 0x04:
            frame = tampon[i:i+25]
            if len(frame) == 25 and crc16(frame[:-2]) == bytes(frame[-2:]):
                regs = []
                for j in range(10):
                    idx = 3 + j * 2
                    val = (frame[idx] << 8) | frame[idx + 1]
                    regs.append(val)

                voltaj      = regs[0] / 10.0
                akim        = ((regs[2] << 16) | regs[1]) / 1000.0
                guc         = ((regs[4] << 16) | regs[3]) / 10.0
                enerji      = (regs[6] << 16) | regs[5]
                frekans     = regs[7] / 10.0
                guc_faktoru = regs[8] / 100.0
                alarm       = regs[9]

                return voltaj, akim, guc, enerji, frekans, guc_faktoru, alarm

    print("❌ Geçerli frame bulunamadı")
    return None

print("🔥 PZEM OKUMA BAŞLADI 🔥")

while True:
    sonuc = read_pzem()
    if sonuc:
        v, i, p, e, f, pf, al = sonuc
        print(f"✅ {v:.1f}V | {i:.3f}A | {p:.1f}W | {e}Wh | {f:.1f}Hz | PF:{pf:.2f} | Alarm:{al}")
    else:
        print("❌ OKUMA HATASI")
    time.sleep(2)