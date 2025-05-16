import serial
import serial.tools.list_ports
from tkinter import *
from tkinter import ttk
from threading import Thread
import psutil
import time
import clr
import os
import sys
from pystray import Icon, MenuItem as item, Menu
from PIL import Image

# --- Load OpenHardwareMonitor DLL ---
dll_path = os.path.join(os.path.dirname(__file__), "OpenHardwareMonitorLib.dll")
clr.AddReference(dll_path)

from OpenHardwareMonitor import Hardware

# Setup hardware monitor
computer = Hardware.Computer()
computer.CPUEnabled = True
computer.GPUEnabled = True
computer.Open()

def get_gpu_load():
    for hardware in computer.Hardware:
        hardware.Update()
        if hardware.HardwareType == Hardware.HardwareType.GpuNvidia or hardware.HardwareType == Hardware.HardwareType.GpuAti:
            for sensor in hardware.Sensors:
                if sensor.SensorType == Hardware.SensorType.Load and "Core" in sensor.Name:
                    return int(sensor.Value or 0)
    return 0

# Serial communication
ser = None
monitoring = False
tray_icon = None

# GUI Setup
root = Tk()
root.title("CPU RAM GPU Monitor")
root.geometry("400x300")
root.configure(bg="#2e3b4e")

# Style
style = ttk.Style()
style.configure("TLabel", foreground="white", background="#2e3b4e", font=("Helvetica", 16))
style.configure("TButton", background="#C0C0C0", foreground="black", font=("Helvetica", 14), padding=10, relief="raised", width=20)
style.map("TButton", foreground=[("pressed", "black"), ("active", "black")], background=[("pressed", "#A9A9A9"), ("active", "#D3D3D3")])
style.configure("TCombobox", font=("Helvetica", 12), padding=5)

cpu_label = ttk.Label(root, text="CPU: 0%")
cpu_label.pack(pady=10)

ram_label = ttk.Label(root, text="RAM: 0%")
ram_label.pack(pady=10)

gpu_label = ttk.Label(root, text="GPU: 0%")
gpu_label.pack(pady=10)

def list_com_ports():
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]

def update_stats():
    global monitoring
    psutil.cpu_percent(interval=None)
    time.sleep(1)
    while monitoring:
        try:
            cpu = psutil.cpu_percent(interval=1)
            ram = psutil.virtual_memory().percent
            gpu = get_gpu_load()

            cpu_label.config(text=f"CPU: {int(cpu)}%")
            ram_label.config(text=f"RAM: {int(ram)}%")
            gpu_label.config(text=f"GPU: {int(gpu)}%")

            if ser and ser.is_open:
                data = f"CPU:{int(cpu)} RAM:{int(ram)} GPU:{int(gpu)}\n"
                ser.write(data.encode())

        except:
            disconnect_serial()
            break
        time.sleep(1)

def start_monitoring():
    global monitoring
    if ser and ser.is_open:
        monitoring = True
        Thread(target=update_stats, daemon=True).start()

def connect_serial():
    global ser
    com_port = com_selector.get()
    try:
        ser = serial.Serial(com_port, 115200, timeout=1)
        start_monitoring()
    except:
        pass

def disconnect_serial():
    global ser, monitoring
    if ser and ser.is_open:
        ser.close()
    monitoring = False

def auto_detect_com_port():
    com_ports = list_com_ports()
    if com_ports:
        com_selector.set(com_ports[0])
        com_menu['values'] = com_ports
        com_menu.current(0)
    else:
        com_selector.set("No COM Ports Found")
    root.after(5000, auto_detect_com_port)

com_selector = StringVar(root)
com_selector.set("Detecting COM Ports...")
com_menu = ttk.Combobox(root, textvariable=com_selector, state="readonly", font=("Helvetica", 12))
com_menu.place(relx=0.95, rely=0.05, anchor=NE, width=120, height=30)

def on_enter(event):
    connect_button.configure(background="#A9A9A9")
def on_leave(event):
    connect_button.configure(background="#C0C0C0")

connect_button = ttk.Button(root, text="🔌 Connect", command=connect_serial)
connect_button.pack(pady=20)
connect_button.bind("<Enter>", on_enter)
connect_button.bind("<Leave>", on_leave)

disconnect_button = ttk.Button(root, text="❌ Disconnect", command=disconnect_serial)
disconnect_button.pack(pady=10)

auto_detect_com_port()

# --- System Tray ---
def restore_window(icon=None, item=None):
    global tray_icon
    if tray_icon:
        tray_icon.stop()
        tray_icon = None
    root.deiconify()

def quit_app(icon=None, item=None):
    global tray_icon
    if tray_icon:
        tray_icon.stop()
    disconnect_serial()
    root.destroy()
    sys.exit()

def create_system_tray_icon():
    global tray_icon
    if tray_icon: return

    icon_path = os.path.join(os.path.dirname(__file__), "HardwareMonitor.ico")
    if not os.path.exists(icon_path):
        return

    image = Image.open(icon_path)
    menu = Menu(item('Restore', restore_window), item('Quit', quit_app))
    tray_icon = Icon("HardwareMonitor", image, "Hardware Monitor", menu)
    Thread(target=tray_icon.run, daemon=True).start()

def on_minimize(event):
    if root.state() == 'iconic':
        root.withdraw()
        create_system_tray_icon()

def on_close():
    root.withdraw()
    create_system_tray_icon()

root.bind("<Unmap>", on_minimize)
root.protocol("WM_DELETE_WINDOW", on_close)

# --- Main ---
root.mainloop()
