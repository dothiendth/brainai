#!/usr/bin/env python3
import os
import json
import time
import subprocess
import csv
from datetime import datetime
import random
import threading
import queue

# Gọi 3 vũ khí tối ưu phần cứng vừa xây dựng
from smart_freezer import SmartFreezer
from cpu_pstate_manager import CPUPStateManager
from battery_protector import BatteryProtector

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEMORY_FILE = os.path.join(BASE_DIR, "brain_memory.json")
LOG_FILE = os.path.join(BASE_DIR, "user_habit_log.csv")
BRAIN_COMMAND_FILE = os.path.join(BASE_DIR, ".brain_command")

ACTIONS = [
    "1. ECO MODE", 
    "2. BALANCE MODE", 
    "3. PERFORMANCE MODE"
]

# === HỆ THỐNG GHI ĐĨA BẤT ĐỒNG BỘ (ASYNC LOGGING) ===
log_queue = queue.Queue()

def async_disk_writer():
    """Luồng thư ký chạy ngầm chuyên chịu trách nhiệm ghi ổ cứng SSD"""
    while True:
        task = log_queue.get()
        if task is None: break
        task_type, data = task
        
        if task_type == "csv":
            try:
                with open(LOG_FILE, "a", encoding="utf-8") as f:
                    csv.writer(f).writerow(data)
                
                # Tự động dọn rác: Xác suất 1% để kiểm tra độ dài (tiết kiệm I/O)
                if random.random() < 0.01:
                    with open(LOG_FILE, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                    if len(lines) > 20000:
                        with open(LOG_FILE, "w", encoding="utf-8") as f:
                            f.writelines(lines[-5000:])
            except: pass
        
        # [BẢN VÁ]: Thêm lệnh xử lý lưu bộ nhớ cho AI
        elif task_type == "memory":
            q_table, epsilon = data
            save_memory(q_table, epsilon)
            
        log_queue.task_done()

# Kích hoạt cô thư ký chạy ngầm ngay khi khởi động file
threading.Thread(target=async_disk_writer, daemon=True).start()

# === BỘ NHỚ ĐỆM ĐƯỜNG DẪN PHẦN CỨNG (I/O MEMOIZATION) ===
HW_PATHS = {
    "bat_status": None, "bat_cap": None, "bat_watt": None, 
    "bat_curr": None, "bat_volt": None, "temp_zones": [], 
    "gpu": None, "gov": "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
}

def init_hardware_paths():
    print("🔍 [SYSTEM] Đang quét và lập bản đồ phần cứng (I/O Cache)...")
    for bat in ["CMB0", "BAT0", "BAT1"]:
        if os.path.exists(f"/sys/class/power_supply/{bat}/status"):
            HW_PATHS["bat_status"] = f"/sys/class/power_supply/{bat}/status"
            HW_PATHS["bat_cap"] = f"/sys/class/power_supply/{bat}/capacity"
            if os.path.exists(f"/sys/class/power_supply/{bat}/power_now"):
                HW_PATHS["bat_watt"] = f"/sys/class/power_supply/{bat}/power_now"
            else:
                HW_PATHS["bat_curr"] = f"/sys/class/power_supply/{bat}/current_now"
                HW_PATHS["bat_volt"] = f"/sys/class/power_supply/{bat}/voltage_now"
            break
            
    for i in range(15):
        t_path = f"/sys/class/thermal/thermal_zone{i}/temp"
        if os.path.exists(t_path): HW_PATHS["temp_zones"].append(t_path)
            
    if os.path.exists("/sys/class/drm/card0/device/gpu_busy_percent"):
        HW_PATHS["gpu"] = "/sys/class/drm/card0/device/gpu_busy_percent"
        
    print(f"✅ [SYSTEM] Đã nạp thành công {len(HW_PATHS['temp_zones'])} cảm biến nhiệt và các Node nguồn!")

def notify_desktop(title, message, urgency="normal"):
    cmd = f'sudo -u lionos DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus notify-send "{title}" "{message}" -u {urgency} -i applications-science'
    subprocess.run(cmd, shell=True)

def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r") as f:
                data = json.load(f)
                if "q_table" in data: 
                    return data["q_table"], data.get("epsilon", 0.5)
                else: 
                    return data, 0.5 
        except Exception: pass
    return {}, 0.5 

def save_memory(q_table, epsilon):
    try:
        with open(MEMORY_FILE, "w") as f:
            json.dump({"epsilon": epsilon, "q_table": q_table}, f, indent=4)
    except Exception as e:
        print(f"⚠️ [LỖI] Không ghi được bộ nhớ JSON: {e}")

def calculate_reward(ac_status, temp, new_temp, watt, app_cpu, chosen_action, gpu_busy):
    reward = 10.0
    temp_delta = new_temp - temp
    
    if new_temp > 85.0: reward -= 60.0
    elif new_temp > 75.0: reward -= 20.0
    
    if temp_delta > 3.0: reward -= 25.0
    elif temp_delta < -2.0: reward += 20.0
        
    if ac_status == "Battery":
        if watt > 12.0: reward -= 40.0 
        if "ECO" in chosen_action: reward += 45.0
        if "PERFORMANCE" in chosen_action: reward -= 70.0
            
    if ac_status == "AC":
        if app_cpu > 45.0:
            if "PERFORMANCE" in chosen_action: reward += 50.0
            if "ECO" in chosen_action: reward -= 40.0
        elif app_cpu < 15.0:
            if "BALANCE" in chosen_action: reward += 25.0
            
    if gpu_busy > 70.0:
        if "PERFORMANCE" in chosen_action: reward += 30.0
        else: reward -= 40.0
                
    return reward

def get_system_stats():
    ac_status = "AC"
    if HW_PATHS["bat_status"]:
        with open(HW_PATHS["bat_status"], "r") as f:
            if f.read().strip() == "Discharging": ac_status = "Battery"
                
    bat_pct = 100
    if HW_PATHS["bat_cap"]:
        with open(HW_PATHS["bat_cap"], "r") as f:
            bat_pct = int(f.read().strip())
            
    watt = 0.0
    if HW_PATHS["bat_watt"]:
        with open(HW_PATHS["bat_watt"], "r") as f:
            watt = float(f.read().strip()) / 1000000.0
    elif HW_PATHS["bat_curr"] and HW_PATHS["bat_volt"]:
        with open(HW_PATHS["bat_curr"], "r") as fc, open(HW_PATHS["bat_volt"], "r") as fv:
            watt = (float(fc.read().strip()) / 1000000.0) * (float(fv.read().strip()) / 1000000.0)
            
    temp = 45.0
    if HW_PATHS["temp_zones"]:
        temps = []
        for t_path in HW_PATHS["temp_zones"]:
            try:
                with open(t_path, "r") as f: temps.append(float(f.read().strip()) / 1000.0)
            except: pass
        if temps: temp = max(temps)
        
    gov = "unknown"
    if os.path.exists(HW_PATHS["gov"]):
        with open(HW_PATHS["gov"], "r") as f: gov = f.read().strip()
            
    top_app = "idle"
    app_cpu = 0.0
    try:
        res = subprocess.run(["ps", "--no-headers", "-eo", "comm,%cpu", "--sort=-%cpu"], capture_output=True, text=True)
        lines = res.stdout.strip().split("\n", 10)
        for line in lines:
            parts = line.split()
            if len(parts) >= 2:
                name = parts[0]
                if name not in ["ps", "top", "brain_gui.py", "BrainAI.py", "python3", "fish", "konsole"]:
                    top_app = name
                    app_cpu = float(parts[1])
                    break
    except Exception: pass

    return ac_status, bat_pct, watt, temp, gov, top_app, app_cpu

def get_gpu_stats():
    gpu_busy = 0.0
    if HW_PATHS["gpu"]:
        try:
            with open(HW_PATHS["gpu"], "r") as f:
                gpu_busy = float(f.read().strip())
        except: pass
    return gpu_busy

def main():
    print("🧠 [BRAIN] Bộ não AI Q-Learning phiên bản 3 Lõi đang khởi động...")

    try:
        os.nice(-5)
    except Exception:
        pass
    
    init_hardware_paths() 
    
    # =========================================================
    # [TÍCH HỢP LÕI]: KHỞI TẠO 3 CÁNH TAY PHẦN CỨNG
    # =========================================================
    freezer = SmartFreezer()
    cpu_manager = CPUPStateManager()
    battery_manager = BatteryProtector()
    
    # Kích hoạt ngắt mạch sạc ở 80% ngay khi bật máy để bảo vệ pin
    battery_manager.set_charge_limit(80)
    # =========================================================
    
    q_table, epsilon = load_memory()
    
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write("Timestamp,Mode,PowerState,Wattage,BatteryPct,BatteryHealth,Temp,Governor,TopApp,AppCPU\n")

    alpha = 0.1
    gamma = 0.9
    epsilon_min = 0.05      
    epsilon_decay = 0.9995  

    notify_desktop("🧠 BrainGram AI Core", "Hệ thống học máy 3 Lõi Thông Minh đã trực tuyến!", "normal")

    last_alert_time = 0
    last_notified_mode = ""

    stable_ac_status = "AC"
    ac_debounce_counter = 0

    while True:
        ac_status_raw, bat_pct, watt, temp, gov, top_app, app_cpu = get_system_stats()
        gpu_busy = get_gpu_stats()
        
        if ac_status_raw != stable_ac_status:
            ac_debounce_counter += 1
            if ac_debounce_counter >= 3: 
                stable_ac_status = ac_status_raw
                ac_debounce_counter = 0
        else:
            ac_debounce_counter = 0
            
        ac_status = stable_ac_status 

        state_power = "AC" if ac_status == "AC" else "BAT"
        state_temp = "HOT" if temp > 76.0 else ("WARM" if temp > 56.0 else "COOL")
        state_load = "HIGH" if app_cpu > 40.0 else ("MED" if app_cpu > 15.0 else "LOW")
        current_state = f"{state_power}_{state_temp}_{state_load}"

        if current_state not in q_table:
            q_table[current_state] = {}
            for act in ACTIONS:
                q_table[current_state][act] = {"score": 0.0, "try_count": 0}

        is_manual = False
        if os.path.exists(BRAIN_COMMAND_FILE):
            try:
                with open(BRAIN_COMMAND_FILE, "r") as f:
                    chosen_action = f.read().strip()
                if chosen_action in ACTIONS: is_manual = True
            except: pass

        if not is_manual:
            if ac_status == "Battery": safe_actions = [a for a in ACTIONS if "PERFORMANCE" not in a]
            else: safe_actions = ACTIONS

            if random.random() < epsilon:
                chosen_action = random.choice(safe_actions)
            else:
                max_score = -99999.0
                chosen_action = safe_actions[0]
                for act in safe_actions:
                    score = q_table[current_state][act]["score"]
                    if score > max_score:
                        max_score = score
                        chosen_action = act

        current_time = time.time()
        if temp > 85.0 and (current_time - last_alert_time) > 60:
            notify_desktop("🔥 AI CẢNH BÁO", f"Nhiệt độ nguy hiểm ({temp:.1f}°C)!", "critical")
            last_alert_time = current_time

        # =========================================================
        # [TÍCH HỢP LÕI]: RA LỆNH CHO PHẦN CỨNG KHI ĐỔI MODE
        # =========================================================
        if chosen_action != last_notified_mode:
            if "PERFORMANCE" in chosen_action: 
                notify_desktop("🚀 AI: PERFORMANCE", "Ép xung tối đa, mở khóa tốc độ!")
                cpu_manager.set_epp("performance")
                freezer.unfreeze_apps()
            elif "ECO" in chosen_action: 
                notify_desktop("🍃 AI: ECO MODE", "Tiết kiệm pin, đóng băng app ngầm.")
                cpu_manager.set_epp("balance_power")
                freezer.freeze_background_apps()
            elif "BALANCE" in chosen_action: 
                notify_desktop("⚖️ AI: BALANCE", "Cân bằng tải thông minh.")
                cpu_manager.set_epp("balance_performance") # Ép xung vừa đủ mượt
                freezer.unfreeze_apps()
                
            last_notified_mode = chosen_action
        # =========================================================

        if not is_manual:
            try:
                with open(BRAIN_COMMAND_FILE, "w") as f: f.write(chosen_action)
            except: pass

        time.sleep(3)

        _, _, new_watt, new_temp, _, _, new_cpu = get_system_stats()
        reward = calculate_reward(ac_status, temp, new_temp, watt, app_cpu, chosen_action, gpu_busy)
        
        if not is_manual:
            if epsilon > epsilon_min:
                epsilon *= epsilon_decay

            old_score = q_table[current_state][chosen_action]["score"]
            q_table[current_state][chosen_action]["score"] = old_score + alpha * (reward - old_score)
            q_table[current_state][chosen_action]["try_count"] += 1

            for state in q_table:
                for action in q_table[state]:
                    q_table[state][action]["score"] *= 0.9999

            log_queue.put(("memory", (q_table, epsilon)))

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        csv_data = [timestamp, chosen_action, ac_status, f"{watt:.2f}", bat_pct, "100", f"{temp:.1f}", gov, top_app, f"{app_cpu:.1f}"]
        log_queue.put(("csv", csv_data))
        log_queue.put(("watt", f"{watt:.2f} W"))

        time.sleep(2)

if __name__ == "__main__":
    main()