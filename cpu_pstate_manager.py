#!/usr/bin/env python3
import os
import glob
import time

class CPUPStateManager:
    def __init__(self):
        # Quét nhân Linux để tìm đường dẫn giao tiếp với toàn bộ các luồng CPU
        self.cpu_cores = glob.glob("/sys/devices/system/cpu/cpu[0-9]*/cpufreq")
        
    def is_root(self):
        """Kiểm tra quyền tối cao (sudo)"""
        return os.geteuid() == 0

    def set_epp(self, mode):
        """
        Thiết lập trạng thái năng lượng.
        Các mode chuẩn: 'performance', 'balance_performance', 'balance_power', 'power'
        """
        if not self.is_root():
            print("❌ LỖI TỪ KERNEL: BrainGramAI cần quyền Root (sudo) để can thiệp vào vi kiến trúc CPU!")
            return False

        success_count = 0
        for core in self.cpu_cores:
            # Đường dẫn của chip đời mới (EPP)
            epp_path = os.path.join(core, "energy_performance_preference")
            # Đường dẫn dự phòng cho chip đời cũ (Governor)
            gov_path = os.path.join(core, "scaling_governor")
            
            try:
                if os.path.exists(epp_path):
                    with open(epp_path, "w") as f:
                        f.write(mode)
                    success_count += 1
                elif os.path.exists(gov_path):
                    # Tự động quy đổi thuật ngữ cho chip cũ
                    gov_mode = "powersave" if "power" in mode else "performance"
                    with open(gov_path, "w") as f:
                        f.write(gov_mode)
                    success_count += 1
            except Exception:
                pass
        
        if success_count > 0:
            print(f"   ⚡ Đã ép {success_count} luồng CPU chuyển sang trạng thái sinh học: {mode.upper()}")
            return True
        else:
            print("   ⚠️ Không tìm thấy trình điều khiển P-State tương thích.")
            return False

# ==========================================
# KHU VỰC TEST THỬ NGHIỆM ĐỘNG CƠ P-STATE
# ==========================================
if __name__ == "__main__":
    manager = CPUPStateManager()
    print("🧠 [BRAINGRAM] Khởi động động cơ kiểm soát phần cứng CPU...")
    
    if not manager.is_root():
        print("🛑 Hãy chạy file này bằng lệnh: sudo ./cpu_pstate_manager.py")
        exit(1)

    print("\n🔋 TÌNH HUỐNG 1: RÚT SẠC (Kích hoạt tiết kiệm pin sâu)")
    manager.set_epp("balance_power")
    
    print("⏳ Giữ trạng thái trong 5 giây...")
    time.sleep(5)
    
    print("\n🚀 TÌNH HUỐNG 2: CẮM SẠC (Mở khóa toàn bộ giới hạn hiệu năng)")
    manager.set_epp("performance")
    print("✅ Hoàn tất bài test P-State!")