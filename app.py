# ==========================================================
# MICROPLASTIC SENSOR DESKTOP APP (UPDATED FOR SENSOR FUSION)
# Architecture: UDP Stream + NumPy Vectorized Heatmap + PIL
# NOW HANDLES: PHOTODIODES + GYRO + ACCEL + BMP280 + GPS
# ==========================================================

import socket
import json
import threading
import time
import os
import csv
import shutil
from datetime import datetime

import tkinter as tk
from tkinter import filedialog, Canvas, Label, Frame, Scale, HORIZONTAL
import numpy as np
from PIL import Image, ImageTk

class SensorDashboard:
    def __init__(self, esp_ip="10.186.247.88", udp_port=8080):
        self.esp_ip = esp_ip
        self.udp_port = udp_port
        
        self.latest = [1.0] * 16  # Photodiode channels
        self.sensors = {}  # All other sensors
        self.sensor_keys = ["T", "P", "HUM", "AX", "AY", "AZ", "GX", "GY", "GZ", "LAT", "LON", "ALT", "SATS"]
        
        self.lock = threading.Lock()
        self.running = True
        self.baseline = 1.0
        
        # --- CSV LOGGING SETUP ---
        self.live_csv = "live_sensor_log.csv"
        self.init_csv()
        
        # --- THEME COLORS ---
        self.bg = "#080c12"
        self.surface = "#0d1420"
        self.border = "#1a2535"
        self.accent = "#00d4ff"   
        self.accent2 = "#00ff9d"  
        self.warn = "#ff9500"     
        self.danger = "#ff3c5a"   
        self.text = "#c8d8e8"
        self.muted = "#4a6070"
        
        # --- THREAD-SAFE UI VARIABLES ---
        self.current_status_text = "Waiting for data..."
        self.current_status_color = self.warn
        self.last_time_str = "--:--:--"
        
        # --- NUMPY HIGH-PERFORMANCE RENDER ENGINE ---
        self.res = 400
        self.init_numpy_engine()
        
        # --- GUI SETUP ---
        self.root = tk.Tk()
        self.root.title("Microplastic Sensor Array [NumPy Engine]")
        self.root.geometry("1000x720") 
        self.root.configure(bg=self.bg)
        
        self.photo_image = None
        
        self.setup_ui()
        
        threading.Thread(target=self.udp_loop, daemon=True).start()
        self.update_display()
        
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.running = False
            self.root.quit()

    def init_numpy_engine(self):
        print("[*] Initializing NumPy Vectorized Engine...")
        grid = 4
        sigma = 52 
        sig2 = 2 * sigma * sigma
        
        X, Y = np.meshgrid(np.arange(self.res), np.arange(self.res))
        self.masks = np.zeros((16, self.res, self.res), dtype=np.float32)
        
        for r in range(grid):
            for c in range(grid):
                i = r * grid + c
                xc = (c + 0.5) * self.res / grid
                yc = (r + 0.5) * self.res / grid
                self.masks[i] = np.exp(-((X - xc)**2 + (Y - yc)**2) / sig2)
                
        stops = [
            (0.00, (0,   0,   180)),
            (0.20, (0,   100, 255)),
            (0.45, (0,   220, 210)),
            (0.55, (180, 255, 100)),
            (0.75, (255, 200,  20)),
            (1.00, (255,  40,   0))
        ]
        
        self.lut = np.zeros((256, 3), dtype=np.uint8)
        for i in range(256):
            t = i / 255.0
            t = max(0.0, min(1.0, t))
            color = (255, 40, 0)
            for j in range(1, len(stops)):
                if t <= stops[j][0]:
                    u = (t - stops[j-1][0]) / (stops[j][0] - stops[j-1][0])
                    c1, c2 = stops[j-1][1], stops[j][1]
                    color = (int(c1[0] + (c2[0] - c1[0]) * u),
                             int(c1[1] + (c2[1] - c1[1]) * u),
                             int(c1[2] + (c2[2] - c1[2]) * u))
                    break
            self.lut[i] = color

    def init_csv(self):
        with open(self.live_csv, 'w', newline='') as f:
            writer = csv.writer(f)
            headers = (["Timestamp"] + 
                      [f"PD{i}" for i in range(16)] + 
                      ["Temp_C", "Pressure_hPa", "Humidity_%", 
                       "Accel_X", "Accel_Y", "Accel_Z",
                       "Gyro_X", "Gyro_Y", "Gyro_Z",
                       "GPS_Lat", "GPS_Lon", "GPS_Alt", "GPS_Sats"])
            writer.writerow(headers)

    def export_csv(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV Files", "*.csv")], title="Export Sensor Data"
        )
        if filepath:
            try:
                shutil.copy(self.live_csv, filepath)
                self.current_status_text = "CSV Exported!"
                self.current_status_color = self.accent2
            except Exception as e:
                self.current_status_text = "Export Failed"
                self.current_status_color = self.danger

    def setup_ui(self):
        header = Frame(self.root, bg=self.surface, highlightbackground=self.border, highlightthickness=1)
        header.pack(fill="x", padx=15, pady=8) 
        Label(header, text="● LIVE", bg=self.surface, fg=self.accent2, font=("Courier", 10, "bold"), bd=1, relief="solid", highlightbackground=self.accent2).pack(side="right", padx=15, pady=5)
        
        title_frame = Frame(header, bg=self.surface)
        title_frame.pack(side="left", padx=15, pady=5)
        Label(title_frame, text="MICROPLASTIC SENSOR ARRAY + ENVIRONMENTAL", bg=self.surface, fg="#ffffff", font=("Arial", 16, "bold")).pack(anchor="w")
        Label(title_frame, text="16-CH PHOTODIODE · GYRO · ACCEL · BMP280 · GPS · UDP · NUMPY ENGINE", bg=self.surface, fg=self.muted, font=("Courier", 9)).pack(anchor="w")

        wrap = Frame(self.root, bg=self.bg)
        wrap.pack(fill="both", expand=True, padx=15, pady=(0, 8))
        
        left = Frame(wrap, bg=self.surface, highlightbackground=self.border, highlightthickness=1)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))
        Label(left, text="SPATIAL INTENSITY MAP — 4×4 ARRAY", bg=self.surface, fg=self.muted, font=("Courier", 10)).pack(pady=(8, 2))
        
        self.canvas = Canvas(left, width=self.res, height=self.res, bg=self.surface, highlightthickness=0)
        self.canvas.pack(pady=2)
        
        legend_frame = Frame(left, bg=self.surface)
        legend_frame.pack(fill="x", padx=30, pady=2)
        self.legend_canvas = Canvas(legend_frame, height=8, bg=self.surface, highlightthickness=0)
        self.legend_canvas.pack(fill="x")
        self.draw_legend()
        
        t_frame = Frame(left, bg=self.surface)
        t_frame.pack(fill="x", padx=30, pady=(4, 4))
        Label(t_frame, text="ANOMALY THRESHOLD:", bg=self.surface, fg=self.muted, font=("Courier", 9)).pack(side="left")
        self.threshold_var = tk.DoubleVar(value=0.05)
        Scale(t_frame, variable=self.threshold_var, from_=0.01, to=0.50, resolution=0.01, orient=HORIZONTAL, bg=self.surface, fg=self.accent, troughcolor=self.bg, highlightthickness=0, length=200).pack(side="right")
        
        # --- ENVIRONMENTAL & MOTION SENSORS DISPLAY ---
        Label(left, text="ENVIRONMENTAL & MOTION SENSORS", bg=self.surface, fg=self.muted, font=("Courier", 10)).pack(pady=(2, 2))
        env_frame = Frame(left, bg=self.surface)
        env_frame.pack(fill="x", padx=20, pady=0)
        
        sensor_configs = [
            ("TEMP", "T", "°C", 0, 0),
            ("PRESS", "P", "hPa", 0, 1),
            ("HUMIDITY", "HUM", "%", 0, 2),
            ("ACCEL X", "AX", "g", 0, 3),
            ("ACCEL Y", "AY", "g", 0, 4),
            ("ACCEL Z", "AZ", "g", 1, 0),
            ("GYRO X", "GX", "°/s", 1, 1),
            ("GYRO Y", "GY", "°/s", 1, 2),
            ("GYRO Z", "GZ", "°/s", 1, 3),
            ("LATITUDE", "LAT", "°", 1, 4),
        ]
        
        self.sensor_lbls = {}
        for title, key, unit, r, c in sensor_configs:
            card = Frame(env_frame, bg=self.bg, highlightbackground=self.border, highlightthickness=1)
            card.grid(row=r, column=c, padx=2, pady=2, sticky="nsew")
            env_frame.grid_columnconfigure(c, weight=1)
            
            Label(card, text=title, bg=self.bg, fg=self.muted, font=("Courier", 7)).pack(pady=(2,0))
            lbl = Label(card, text="--", bg=self.bg, fg=self.accent2, font=("Courier", 11, "bold"))
            lbl.pack(pady=0)
            Label(card, text=unit, bg=self.bg, fg=self.muted, font=("Courier", 7)).pack(pady=(0,2))
            self.sensor_lbls[key] = lbl
        
        # GPS Info Card
        gps_frame = Frame(env_frame, bg=self.bg, highlightbackground=self.border, highlightthickness=1)
        gps_frame.grid(row=0, column=5, rowspan=2, padx=2, pady=2, sticky="nsew")
        Label(gps_frame, text="GPS", bg=self.bg, fg=self.muted, font=("Courier", 7)).pack(pady=(2,0))
        self.gps_lbl = Label(gps_frame, text="No Fix", bg=self.bg, fg=self.warn, font=("Courier", 9))
        self.gps_lbl.pack(pady=2)
        self.gps_lon_lbl = Label(gps_frame, text="--°", bg=self.bg, fg=self.text, font=("Courier", 8))
        self.gps_lon_lbl.pack(pady=1)
        self.gps_alt_lbl = Label(gps_frame, text="--m", bg=self.bg, fg=self.text, font=("Courier", 8))
        self.gps_alt_lbl.pack(pady=(1,2))
        
        right = Frame(wrap, bg=self.bg, width=280)
        right.pack(side="right", fill="both")
        right.pack_propagate(False)
        
        self.anom_lbl = self.make_stat_card(right, "ANOMALIES DETECTED", "0", sub_text="channels > ±0.05 from baseline")
        self.peak_lbl = self.make_stat_card(right, "PEAK CHANNEL", "CH-- · 0.000", self.warn)
        self.time_lbl = self.make_stat_card(right, "LAST UPDATED", "--:--:--", self.text, 14)
        self.status_lbl = self.make_stat_card(right, "STATUS", "Waiting for data...", self.warn, 12)
        
        ch_panel = Frame(right, bg=self.surface, highlightbackground=self.border, highlightthickness=1)
        ch_panel.pack(fill="x", pady=(0, 5))
        Label(ch_panel, text="PHOTODIODE CHANNELS", bg=self.surface, fg=self.muted, font=("Courier", 9)).pack(anchor="w", padx=10, pady=(5, 2))
        
        grid_frame = Frame(ch_panel, bg=self.surface)
        grid_frame.pack(fill="both", expand=True, padx=10, pady=2)
        
        self.ch_bars = []
        for i in range(16):
            r, c = i // 4, i % 4
            cell = Frame(grid_frame, bg=self.bg, highlightbackground=self.border, highlightthickness=1, width=50, height=45)
            cell.grid(row=r, column=c, padx=2, pady=2)
            cell.pack_propagate(False)
            
            c_bar = Canvas(cell, bg=self.bg, highlightthickness=0)
            c_bar.place(relwidth=1.0, relheight=1.0)
            lbl_val = Label(cell, text="1.00", bg=self.bg, fg=self.text, font=("Courier", 8))
            lbl_val.pack(side="top", pady=(2, 0))
            lbl_ch = Label(cell, text=f"PD{i}", bg=self.bg, fg=self.muted, font=("Courier", 7))
            lbl_ch.pack(side="bottom")
            self.ch_bars.append({"canvas": c_bar, "val": lbl_val, "ch": lbl_ch, "bg": cell})

        btn = tk.Button(right, text="⬇ Download CSV", bg=self.surface, fg=self.accent, activebackground=self.accent, activeforeground=self.bg, font=("Courier", 10, "bold"), bd=1, relief="solid", command=self.export_csv)
        btn.pack(fill="x", pady=(5, 0), ipady=5)

    def make_stat_card(self, parent, title, val, val_color=None, font_size=24, sub_text=None):
        if val_color is None: val_color = self.accent
        card = Frame(parent, bg=self.surface, highlightbackground=self.border, highlightthickness=1)
        card.pack(fill="x", pady=(0, 6))
        Label(card, text=title, bg=self.surface, fg=self.muted, font=("Courier", 9)).pack(anchor="w", padx=10, pady=(6, 0))
        lbl = Label(card, text=val, bg=self.surface, fg=val_color, font=("Courier", font_size, "bold"))
        lbl.pack(anchor="w", padx=10, pady=(0, 2))
        if sub_text:
            Label(card, text=sub_text, bg=self.surface, fg=self.muted, font=("Courier", 8)).pack(anchor="w", padx=10, pady=(0, 6))
        return lbl

    def draw_legend(self):
        width = 340
        for i in range(width):
            color = "#{:02x}{:02x}{:02x}".format(*self.lut[int((i/width)*255)])
            self.legend_canvas.create_line(i, 0, i, 10, fill=color)

    def udp_loop(self):
        """Receives data from ESP32 with proper JSON structure parsing"""
        client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_sock.settimeout(1.0)
        
        if os.name == 'nt':
            try: 
                client_sock.ioctl(socket.SIO_UDP_CONNRESET, False)
            except Exception: 
                pass
        
        while self.running:
            try:
                client_sock.sendto(b"GET_DATA", (self.esp_ip, self.udp_port))
                data, addr = client_sock.recvfrom(4096)  # Increased to handle all sensor data
                parsed_data = json.loads(data.decode())
                
                with self.lock:
                    # Extract photodiode data
                    if "photodiodes" in parsed_data:
                        self.latest = parsed_data["photodiodes"]
                    
                    # Extract all sensor data
                    sensors_dict = {}
                    
                    # BMP280 (Temperature, Pressure) -> Switched to bmp280 here
                    if "bmp280" in parsed_data:
                        bmp = parsed_data["bmp280"]
                        sensors_dict["T"] = bmp.get("temperature", 0.0)
                        sensors_dict["P"] = bmp.get("pressure", 0.0)
                        sensors_dict["HUM"] = bmp.get("humidity", 0.0) # Gracefully defaults to 0.0
                    
                    # Accelerometer
                    if "accelerometer" in parsed_data:
                        accel = parsed_data["accelerometer"]
                        sensors_dict["AX"] = accel.get("x", 0.0)
                        sensors_dict["AY"] = accel.get("y", 0.0)
                        sensors_dict["AZ"] = accel.get("z", 0.0)
                    
                    # Gyroscope
                    if "gyroscope" in parsed_data:
                        gyro = parsed_data["gyroscope"]
                        sensors_dict["GX"] = gyro.get("x", 0.0)
                        sensors_dict["GY"] = gyro.get("y", 0.0)
                        sensors_dict["GZ"] = gyro.get("z", 0.0)
                    
                    # GPS
                    if "gps" in parsed_data:
                        gps = parsed_data["gps"]
                        sensors_dict["LAT"] = gps.get("latitude", 0.0)
                        sensors_dict["LON"] = gps.get("longitude", 0.0)
                        sensors_dict["ALT"] = gps.get("altitude", 0.0)
                        sensors_dict["SATS"] = gps.get("satellites", 0)
                    
                    self.sensors = sensors_dict
                
                # Log to CSV
                with open(self.live_csv, 'a', newline='') as f:
                    writer = csv.writer(f)
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                    sensor_row = [
                        self.sensors.get("T", 0.0),
                        self.sensors.get("P", 0.0),
                        self.sensors.get("HUM", 0.0),
                        self.sensors.get("AX", 0.0),
                        self.sensors.get("AY", 0.0),
                        self.sensors.get("AZ", 0.0),
                        self.sensors.get("GX", 0.0),
                        self.sensors.get("GY", 0.0),
                        self.sensors.get("GZ", 0.0),
                        self.sensors.get("LAT", 0.0),
                        self.sensors.get("LON", 0.0),
                        self.sensors.get("ALT", 0.0),
                        self.sensors.get("SATS", 0),
                    ]
                    writer.writerow([timestamp] + self.latest + sensor_row)
                
                self.current_status_text = "Streaming · 16 PD + 10 Sensors"
                self.current_status_color = self.accent2
                self.last_time_str = datetime.now().strftime("%H:%M:%S")
                
            except socket.timeout:
                self.current_status_text = "Timeout - ESP32 Off"
                self.current_status_color = self.danger
            except ConnectionResetError:
                self.current_status_text = "ESP32 Refused"
                self.current_status_color = self.danger
            except Exception as e:
                print(f"UDP Error: {e}")
                
            time.sleep(0.1)

    def update_display(self):
        """Main display update loop"""
        if not self.running: return
        with self.lock: 
            vals = self.latest[:]
            sens = self.sensors.copy()
        threshold = self.threshold_var.get()
        
        # Update status
        self.status_lbl.config(text=self.current_status_text, fg=self.current_status_color)
        self.time_lbl.config(text=self.last_time_str)
        
        # Display Sensor Data
        for key, lbl in self.sensor_lbls.items():
            if key in sens:
                if key in ["LAT", "LON"]:
                    lbl.config(text=f"{sens[key]:.5f}")
                elif key == "SATS":
                    lbl.config(text=f"{int(sens[key])}")
                else:
                    lbl.config(text=f"{sens[key]:.2f}")
        
        # GPS Card
        if "LAT" in sens and "LON" in sens:
            self.gps_lbl.config(text=f"[✓] {int(sens.get('SATS', 0))} Sats", fg=self.accent2)
            self.gps_lon_lbl.config(text=f"{sens['LON']:.4f}°")
        if "ALT" in sens:
            self.gps_alt_lbl.config(text=f"{sens['ALT']:.1f}m")
        
        # --- PHOTODIODE HEATMAP RENDERING ---
        amps = np.array(vals, dtype=np.float32) - self.baseline
        field = np.tensordot(amps, self.masks, axes=1)
        mx = max(np.max(np.abs(field)), 0.0001)
        t_normalized = (field + mx) / (2 * mx)
        indices = np.clip(t_normalized * 255, 0, 255).astype(np.uint8)
        
        rgb_image = self.lut[indices]
        img = Image.fromarray(rgb_image, 'RGB')
        
        self.photo_image = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.photo_image, anchor="nw")
        
        # --- PHOTODIODE OVERLAYS & BARS ---
        cell_w = 100
        anomalies, peak_val, peak_idx = 0, 0, 0
        v_min, v_max = min(vals), max(vals)
        span = (v_max - v_min) if (v_max - v_min) > 0 else 1.0
        
        for i in range(16):
            r, c = i // 4, i % 4
            x0, y0 = c * cell_w, r * cell_w
            
            self.canvas.create_rectangle(x0, y0, x0+cell_w, y0+cell_w, outline="#1a4555", width=1)
            
            val = vals[i]
            abs_delta = abs(val - self.baseline)
            
            if abs_delta > threshold: anomalies += 1
            if abs_delta > abs(peak_val - self.baseline):
                peak_val = val
                peak_idx = i
                
            is_anom = abs_delta > threshold
            lbl_color = "#ffffff" if is_anom else "#6a8a9e" 
            val_color = "#ffdd00" if is_anom else "#6a8a9e" 
            
            self.canvas.create_text(x0 + cell_w/2, y0 + cell_w/2 - 10, text=f"PD{i}", fill=lbl_color, font=("Courier", 11, "bold"))
            self.canvas.create_text(x0 + cell_w/2, y0 + cell_w/2 + 10, text=f"{val:.3f}", fill=val_color, font=("Courier", 12))
            
            pct = max(0.05, (val - v_min) / span)
            bar_color = self.danger if is_anom else self.accent
            bar_ui = self.ch_bars[i]
            bar_ui["canvas"].delete("all")
            bar_ui["canvas"].create_rectangle(0, 45 - (45 * pct), 50, 45, fill=bar_color, outline="")
            bar_ui["val"].config(text=f"{val:.2f}", bg=bar_color if pct > 0.8 else self.bg)
            bar_ui["ch"].config(bg=bar_color if pct > 0.5 else self.bg)
            
        self.anom_lbl.config(text=str(anomalies), fg=self.danger if anomalies > 3 else self.accent)
        self.peak_lbl.config(text=f"PD{peak_idx} · {peak_val:.3f}")
        
        self.root.after(40, self.update_display)

if __name__ == "__main__":
    app = SensorDashboard(esp_ip="10.186.247.88", udp_port=8080)