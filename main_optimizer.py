#!/usr/bin/env python3
import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Tự động lấy đường dẫn chuẩn cùng thư mục với GUI và Brain
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BRAIN_COMMAND_FILE = os.path.join(BASE_DIR, ".brain_command")

def apply_hardware_settings(mode):
    print(f"⚡ [EXECUTOR] Đang ép phần cứng ngoại vi chạy theo Profile: {mode}")
    
    if "ECO" in mode:
        # 1. Tối ưu Nhân xử lý (Đã nhường EPP cho BrainAI, chỉ giữ lại Turbo Boost)
        os.system("echo 1 | tee /sys/devices/system/cpu/intel_pstate/no_turbo > /dev/null 2>&1") 
        
        # 2. Cắt điện các thiết bị Ngoại vi
        os.system("iw dev wlp0s20f3 set power_save on > /dev/null 2>&1")
        os.system("echo 1 | tee /sys/module/snd_hda_intel/parameters/power_save > /dev/null 2>&1")
        os.system("echo min_power | tee /sys/class/scsi_host/host*/link_power_management_policy > /dev/null 2>&1")
        
        # 3. Đóng băng các Dịch vụ ngầm của Hệ điều hành (Kết hợp với SmartFreezer của BrainAI)
        os.system("sudo -u lionos balooctl6 suspend > /dev/null 2>&1") # Dừng bộ index file của KDE
        os.system("systemctl stop docker.service > /dev/null 2>&1") # Tắt Docker nếu đang chạy

    elif "BALANCE" in mode:
        # 1. Mở lại Turbo Boost nhưng để hệ thống tự cân bằng
        os.system("echo 0 | tee /sys/devices/system/cpu/intel_pstate/no_turbo > /dev/null 2>&1")
        
        # 2. Đánh thức phần cứng ngoại vi
        os.system("iw dev wlp0s20f3 set power_save off > /dev/null 2>&1")
        os.system("echo 0 | tee /sys/module/snd_hda_intel/parameters/power_save > /dev/null 2>&1")
        os.system("echo max_performance | tee /sys/class/scsi_host/host*/link_power_management_policy > /dev/null 2>&1")
        
        # 3. Khôi phục dịch vụ
        os.system("sudo -u lionos balooctl6 resume > /dev/null 2>&1")

    elif "PERFORMANCE" in mode:
        # 1. Quái thú: Cho phép CPU vượt rào Turbo Boost
        os.system("echo 0 | tee /sys/devices/system/cpu/intel_pstate/no_turbo > /dev/null 2>&1")
        
        # 2. Bơm điện tối đa cho mạch ngoại vi
        os.system("iw dev wlp0s20f3 set power_save off > /dev/null 2>&1")
        os.system("echo 0 | tee /sys/module/snd_hda_intel/parameters/power_save > /dev/null 2>&1")
        os.system("echo max_performance | tee /sys/class/scsi_host/host*/link_power_management_policy > /dev/null 2>&1")
        
        # 3. Khôi phục dịch vụ
        os.system("sudo -u lionos balooctl6 resume > /dev/null 2>&1")
        # (Bạn có thể bỏ comment dòng dưới nếu muốn tự bật lại Docker khi cắm sạc)
        # os.system("systemctl start docker.service > /dev/null 2>&1")

def read_and_apply():
    if os.path.exists(BRAIN_COMMAND_FILE):
        try:
            with open(BRAIN_COMMAND_FILE, "r") as f:
                target_mode = f.read().strip()
            if target_mode:
                apply_hardware_settings(target_mode)
        except Exception as e:
            print(f"⚠️ [LỖI] Cơ bắp không đọc được lệnh: {e}")

class CommandHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith(".brain_command"):
            read_and_apply()
            
    def on_created(self, event):
        if event.src_path.endswith(".brain_command"):
            read_and_apply()

def main():
    print(f"▶️ Hệ thống Cơ bắp (Executor) đang túc trực (Watchdog) tại: {BASE_DIR}")
    
    # Chạy lệnh áp dụng phần cứng ngay lần đầu tiên
    read_and_apply()
    
    # Thiết lập bộ lắng nghe sự kiện
    event_handler = CommandHandler()
    observer = Observer()
    observer.schedule(event_handler, path=BASE_DIR, recursive=False)
    observer.start()
    
    try:
        while True:
            # Ngủ đông hoàn toàn, chỉ thức dậy khi file bị thay đổi (Zero CPU Usage)
            time.sleep(3600) 
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("🛑 Dừng lại! Executor (Cơ bắp) cần quyền ROOT để can thiệp mạch điện hệ thống.")
        exit(1)
    main()