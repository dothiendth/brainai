#!/usr/bin/env python3
import os
import glob

class BatteryProtector:
    def __init__(self):
        self.target_file = None
        self.detect_hardware_threshold_file()

    def is_root(self):
        return os.geteuid() == 0

    def detect_hardware_threshold_file(self):
        """Hệ thống quét thông minh: Tìm kiếm file cấu hình mạch sạc trên mọi phân vùng phần cứng"""
        # Danh sách các file điều khiển sạc phổ biến của các hãng (ASUS, Lenovo, MSI, Dell, HP, ThinkPad...)
        threshold_names = [
            "charge_control_end_threshold", # ASUS, Lenovo đời mới, MSI
            "charge_stop_threshold",        # Lenovo ThinkPad
            "charge_control_limit_max",     # Một số dòng ASUS cũ
        ]

        # 1. Quét diện rộng trong phân vùng quản lý năng lượng hệ thống
        all_power_supplies = glob.glob("/sys/class/power_supply/*")
        for supply_path in all_power_supplies:
            for name in threshold_names:
                test_path = os.path.join(supply_path, name)
                if os.path.exists(test_path):
                    self.target_file = test_path
                    return

        # 2. Quét diện rộng trong phân vùng driver nền tảng (Platform drivers dành cho dòng máy đặc thù)
        platform_paths = [
            "/sys/devices/platform/asus-nb-wmi/charge_control_end_threshold", # Bản vá riêng cho ASUS ROG/TUF
            "/sys/devices/platform/huawei-wmi/charge_control_threshold",     # Máy Huawei MateBook
        ]
        for path in platform_paths:
            if os.path.exists(path):
                self.target_file = path
                return

    def set_charge_limit(self, limit_value):
        """Ghi ngưỡng ngắt sạc trực tiếp vào mạch phần cứng sau khi đã dò được file"""
        if not self.is_root():
            print("❌ LỖI KERNEL: Cần quyền Root (sudo) để can thiệp mạch sạc phần cứng!")
            return False

        if not self.target_file:
            print("⚠️ [THẤT BẠI] Hệ thống đã quét toàn bộ Kernel nhưng không tìm thấy file ngắt sạc phần cứng.")
            print("👉 Có thể chip điều khiển nguồn (EC) của dòng máy này yêu cầu driver độc quyền chưa được nạp.")
            return False

        try:
            # Ghi cấu hình giới hạn vào file phần cứng
            with open(self.target_file, "w") as f:
                f.write(str(limit_value))
            print(f"   🎯 ĐÃ TÌM THẤY PHẦN CỨNG TẠI: {self.target_file}")
            print(f"   🔋 [BATTERY] Mạch sạc sinh học đã được cấu hình thành công! Sẽ ngắt ở: {limit_value}%")
            return True
        except Exception as e:
            print(f"   ❌ Lỗi ghi dữ liệu vào vi mạch: {e}")
            return False

# ==========================================
# KHU VỰC THỰC THI CHƯƠNG TRÌNH
# ==========================================
if __name__ == "__main__":
    protector = BatteryProtector()
    print("🧠 [BRAINGRAM] Khởi động mô-đun Quản trị Mạch sạc Sinh học (Bản quét thông minh)...")

    if not protector.is_root():
        print("🛑 Hãy chạy file này bằng lệnh: sudo ./battery_protector.py")
        exit(1)

    print("\n🛡️ Đang dò tìm phần cứng và áp dụng Chế độ Bảo vệ Pin (Giới hạn 80%):")
    protector.set_charge_limit(80)