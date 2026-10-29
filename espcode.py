# ==========================================================
# ESP32 MicroPython - COMPLETE SENSOR FUSION SERVER
# MATCHED TO USER'S SPECIFIC STM32 C CODE (Time, CH0..15)
# ==========================================================

from machine import UART, I2C, Pin
import network
import socket
import time
import ujson
import gc
import ustruct

# ==========================================================
# CONFIGURATION
# ==========================================================
SSID = "Ameya Phone"
PASSWORD = "Ameya@1967"
UART_BAUDRATE = 115200
UDP_PORT = 8080

I2C_SCL, I2C_SDA, I2C_FREQ = 22, 21, 400000
STM32_UART_NUM, STM32_UART_TX, STM32_UART_RX = 2, 17, 16
GPS_UART_NUM, GPS_UART_TX, GPS_UART_RX = 1, 5, 18

BMP280_ADDR = 0x76
MPU6050_ADDR = 0x68

# ==========================================================
# DATA STORAGE
# ==========================================================
latest_photodiode_data = [1.0] * 16
latest_gyro_data = {"x": 0.0, "y": 0.0, "z": 0.0}
latest_accel_data = {"x": 0.0, "y": 0.0, "z": 0.0}
latest_bmp280_data = {"temperature": 0.0, "pressure": 0.0}
latest_gps_data = {"latitude": 0.0, "longitude": 0.0, "altitude": 0.0, "satellites": 0, "fix": "No Fix", "time": ""}

uart_buffer = ""

# ==========================================================
# INITIALIZATION
# ==========================================================
print("[*] Initializing UARTs...")
uart_stm32 = UART(STM32_UART_NUM, baudrate=UART_BAUDRATE, tx=STM32_UART_TX, rx=STM32_UART_RX)
uart_gps = UART(GPS_UART_NUM, baudrate=9600, tx=GPS_UART_TX, rx=GPS_UART_RX)

print("[*] Initializing I2C...")
i2c = I2C(0, scl=Pin(I2C_SCL), sda=Pin(I2C_SDA), freq=I2C_FREQ)
devices = i2c.scan()
print(f"[✓] Found I2C devices at: {[hex(addr) for addr in devices]}")

print("[*] Initializing WiFi...")
wifi = network.WLAN(network.STA_IF)
wifi.active(True)
if not wifi.isconnected():
    wifi.connect(SSID, PASSWORD)
    while not wifi.isconnected():
        time.sleep(1)
try: wifi.config(pm=0)
except: pass
print(f"[✓] WiFi Connected: {wifi.ifconfig()[0]}")

# ==========================================================
# DRIVERS (BMP280 & MPU6050)
# ==========================================================
class BMP280:
    def __init__(self, i2c, addr=0x76):
        self.i2c = i2c
        self.addr = addr
        self.initialized = False
        try:
            calib1 = self.i2c.readfrom_mem(self.addr, 0x88, 24)
            self.dig_T1 = ustruct.unpack('<H', calib1[0:2])[0]
            self.dig_T2 = ustruct.unpack('<h', calib1[2:4])[0]
            self.dig_T3 = ustruct.unpack('<h', calib1[4:6])[0]
            self.dig_P1 = ustruct.unpack('<H', calib1[6:8])[0]
            self.dig_P2 = ustruct.unpack('<h', calib1[8:10])[0]
            self.dig_P3 = ustruct.unpack('<h', calib1[10:12])[0]
            self.dig_P4 = ustruct.unpack('<h', calib1[12:14])[0]
            self.dig_P5 = ustruct.unpack('<h', calib1[14:16])[0]
            self.dig_P6 = ustruct.unpack('<h', calib1[16:18])[0]
            self.dig_P7 = ustruct.unpack('<h', calib1[18:20])[0]
            self.dig_P8 = ustruct.unpack('<h', calib1[20:22])[0]
            self.dig_P9 = ustruct.unpack('<h', calib1[22:24])[0]
            self.initialized = True
            print("[✓] BMP280 Initialized")
        except Exception as e:
            print(f"[!] BMP280 Init Failed: {e}")

    def read(self):
        if not self.initialized: return 0, 0
        try:
            data = self.i2c.readfrom_mem(self.addr, 0xF7, 6)
            adc_P = (data[0] << 12) | (data[1] << 4) | (data[2] >> 4)
            adc_T = (data[3] << 12) | (data[4] << 4) | (data[5] >> 4)

            var1 = ((adc_T >> 3) - (self.dig_T1 << 1)) * self.dig_T2 >> 11
            var2 = (((adc_T >> 4) - self.dig_T1) * ((adc_T >> 4) - self.dig_T1) >> 12) * self.dig_T3 >> 14
            t_fine = var1 + var2
            temp = ((t_fine * 5 + 128) >> 8) / 100.0

            var1 = (t_fine >> 1) - 64000
            var2 = (((var1 >> 2) * (var1 >> 2)) >> 11) * self.dig_P6
            var2 = var2 + ((var1 * self.dig_P5) << 1)
            var2 = (var2 >> 2) + (self.dig_P4 << 16)
            var1 = (((self.dig_P3 * (((var1 >> 2) * (var1 >> 2)) >> 13)) >> 3) + ((self.dig_P2 * var1) >> 1)) >> 18
            var1 = ((32768 + var1) * self.dig_P1) >> 15
            if var1 == 0: return temp, 0
            p = ((1048576 - adc_P) - (var2 >> 12)) * 3125
            if p < 0x80000000: p = (p << 1) // var1
            else: p = (p // var1) * 2
            var1 = (self.dig_P9 * (((p >> 3) * (p >> 3)) >> 13)) >> 12
            var2 = (((p >> 2)) * self.dig_P8) >> 13
            pres = (p + ((var1 + var2 + self.dig_P7) >> 4)) / 100.0
            return temp, pres
        except:
            return 0, 0

class MPU6050:
    def __init__(self, i2c, addr=0x68):
        self.i2c = i2c
        self.addr = addr
        self.initialized = False
        try:
            self.i2c.writeto_mem(self.addr, 0x6B, b'\x00') # Wake up
            self.initialized = True
            print("[✓] MPU6050 Initialized")
        except:
            print("[!] MPU6050 Init Failed")

    def read(self):
        if not self.initialized: return None, None
        try:
            data = self.i2c.readfrom_mem(self.addr, 0x3B, 14)
            ax, ay, az, t, gx, gy, gz = ustruct.unpack('>hhhhhhh', data)
            accel = {"x": ax/16384.0, "y": ay/16384.0, "z": az/16384.0}
            gyro = {"x": gx/131.0, "y": gy/131.0, "z": gz/131.0}
            return accel, gyro
        except:
            return None, None

class GPSParser:
    def __init__(self): self.buffer = b""
    def parse_gprmc(self, sentence):
        try:
            if sentence.startswith(b'$GPRMC'):
                parts = sentence.split(b',')
                if len(parts) > 7 and parts[2] == b'A':
                    lat_deg = float(parts[3][0:2].decode()) + float(parts[3][2:].decode()) / 60.0
                    lat = -lat_deg if parts[4] == b'S' else lat_deg
                    lon_deg = float(parts[5][0:3].decode()) + float(parts[5][3:].decode()) / 60.0
                    lon = -lon_deg if parts[6] == b'W' else lon_deg
                    return {'lat': lat, 'lon': lon, 'time': parts[1].decode()}
        except: pass
        return None

# ==========================================================
# INSTANTIATE DEVICES
# ==========================================================
bmp280 = BMP280(i2c) if BMP280_ADDR in devices else None
mpu6050 = MPU6050(i2c) if MPU6050_ADDR in devices else None
gps_parser = GPSParser()

# ==========================================================
# CUSTOMIZED STM32 PARSER
# ==========================================================
def parse_stm32_uart():
    """ Parses format: [Time], CH0, CH1 ... CH15 """
    global latest_photodiode_data, uart_buffer
    
    if uart_stm32.any():
        try:
            uart_buffer += uart_stm32.read().decode('utf-8')
            if '\n' in uart_buffer:
                lines = uart_buffer.split('\n')
                
                for line in lines[:-1]:
                    line = line.strip()
                    
                    # Ignore the header line or empty lines
                    if not line or line.startswith("Time"):
                        continue
                        
                    parts = line.split(",")
                    
                    # The STM sends 17 values: Time + 16 channels
                    if len(parts) >= 17:
                        try:
                            # Skip parts[0] (which is Time), parse the 16 channels
                            parsed_values = [float(x) for x in parts[1:17]]
                            if len(parsed_values) == 16:
                                latest_photodiode_data = parsed_values
                        except ValueError:
                            pass # Skip lines with corrupted data
                            
                uart_buffer = lines[-1] # Keep the incomplete line for the next loop
        except Exception as e:
            uart_buffer = "" # Reset buffer on decoding errors

def parse_gps_uart():
    global latest_gps_data
    if uart_gps.any():
        try:
            char = uart_gps.read(1)
            if char == b'\n':
                s = gps_parser.buffer.strip()
                gps_parser.buffer = b""
                data = gps_parser.parse_gprmc(s)
                if data:
                    latest_gps_data['latitude'] = data['lat']
                    latest_gps_data['longitude'] = data['lon']
                    latest_gps_data['fix'] = 'Fix Acquired'
            else:
                gps_parser.buffer += char
        except: gps_parser.buffer = b""

# ==========================================================
# SERVER LOOP
# ==========================================================
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", UDP_PORT))
sock.setblocking(False)

print(f"\n[✓] UDP Server listening on port {UDP_PORT}")
last_gc = time.time()
last_sensor_read = time.time()

while True:
    current_time = time.time()
    
    # 1. Update UART data
    parse_stm32_uart()
    parse_gps_uart()
    
    # 2. Update I2C Sensors periodically
    if current_time - last_sensor_read > 0.05:
        if bmp280:
            t, p = bmp280.read()
            latest_bmp280_data = {"temperature": t, "pressure": p}
        if mpu6050:
            acc, gyr = mpu6050.read()
            if acc: latest_accel_data, latest_gyro_data = acc, gyr
        last_sensor_read = current_time
        
    # 3. Handle UDP Requests
    try:
        data, addr = sock.recvfrom(1024)
        if data == b"GET_DATA":
            response = ujson.dumps({
                "photodiodes": latest_photodiode_data,
                "gyroscope": latest_gyro_data,
                "accelerometer": latest_accel_data,
                "bmp280": latest_bmp280_data,
                "gps": latest_gps_data
            })
            sock.sendto(response.encode('utf-8'), addr)
    except OSError: pass

    # 4. Memory Management
    if current_time - last_gc > 5:
        gc.collect()
        last_gc = current_time
        
    time.sleep(0.002)
