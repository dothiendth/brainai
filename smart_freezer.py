#!/usr/bin/env python3
import psutil
import os
import signal
import time
import threading
import subprocess

class SmartFreezer:
    def __init__(self):
        # Đã loại bỏ 'chrome', 'brave', 'firefox' để bạn lướt web làm việc mượt mà
        # Chỉ đóng băng các app liên lạc/chạy ngầm ngốn pin
        self.target_apps = ["discord", "slack", "telegram-desktop", "skype", "zalo"]
        self.frozen_pids = set()
        
        # Biến điều khiển luồng Mắt thần
        self.monitor_running = True
        # Khởi động luồng Mắt thần theo dõi cửa sổ đang dùng
        threading.Thread(target=self._auto_wake_monitor, daemon=True).start()

    def _get_active_pid(self):
        """Hàm dùng công cụ hệ thống để lấy PID của cửa sổ đang được dùng (focus)"""
        try:
            # Lấy ID cửa sổ hiện tại (yêu cầu xdotool)
            window_id = subprocess.check_output(["xdotool", "getactivewindow"], stderr=subprocess.DEVNULL).decode().strip()
            # Từ ID cửa sổ, truy ngược ra mã tiến trình (PID)
            pid = subprocess.check_output(["xdotool", "getwindowpid", window_id], stderr=subprocess.DEVNULL).decode().strip()
            return int(pid)
        except Exception:
            return -1

    def _auto_wake_monitor(self):
        """Luồng chạy ngầm: Tự động Rã đông app nếu người dùng click vào"""
        while self.monitor_running:
            active_pid = self._get_active_pid()
            
            # Nếu app đang được click nằm trong danh sách đang bị đóng băng
            if active_pid != -1 and active_pid in self.frozen_pids:
                print(f"\n👀 [MẮT THẦN] Phát hiện bạn đang focus vào app (PID: {active_pid}). Rã đông tức thì!")
                try:
                    os.kill(active_pid, signal.SIGCONT) # Đánh thức riêng app này
                    self.frozen_pids.remove(active_pid)
                except Exception:
                    pass
                    
            time.sleep(1) # Quét cửa sổ 1 giây 1 lần để tiết kiệm CPU

    def get_target_pids(self):
        """Quét toàn bộ hệ thống để tìm PID của các ứng dụng trong danh sách đen."""
        pids = []
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                proc_name = proc.info['name'].lower()
                if any(app in proc_name for app in self.target_apps):
                    pids.append(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return pids

    def freeze_background_apps(self):
        """Hành động: Bắn tia đóng băng (SIGSTOP) vào các ứng dụng ngốn pin."""
        print("❄️ [BRAINGRAM] Kích hoạt chế độ Đóng Băng Tối thượng...")
        pids = self.get_target_pids()
        count = 0
        
        for pid in pids:
            # Bỏ qua app đang được focus hiện tại (không đóng băng app đang dùng)
            if pid == self._get_active_pid():
                continue
                
            if pid not in self.frozen_pids:
                try:
                    os.kill(pid, signal.SIGSTOP) # Lệnh ép dừng cấp thấp của Linux
                    self.frozen_pids.add(pid)
                    count += 1
                except Exception:
                    pass
                    
        print(f"   => Đã khóa {count} tiến trình. CPU hiện tại không bị làm phiền!")
        return count

    def unfreeze_apps(self):
        """Hành động: Rã đông (SIGCONT) trả lại trạng thái bình thường."""
        if not self.frozen_pids:
            return 0
            
        print("🔥 [BRAINGRAM] Đang Rã đông hệ thống...")
        count = 0
        # Dùng list() để tránh lỗi thay đổi set trong khi lặp
        for pid in list(self.frozen_pids):
            try:
                os.kill(pid, signal.SIGCONT) # Lệnh đánh thức
                count += 1
            except Exception:
                pass
            finally:
                self.frozen_pids.remove(pid)
                
        print(f"   => Đã đánh thức {count} tiến trình phục vụ người dùng.")
        return count

# ==========================================
# KHU VỰC TEST THỬ NGHIỆM ĐỘNG CƠ
# ==========================================
if __name__ == "__main__":
    freezer = SmartFreezer()
    
    print("Mở một trình duyệt hoặc Discord lên để test nhé!")
    time.sleep(3)
    
    freezer.freeze_background_apps()
    print("⏳ Đang giữ trạng thái đóng băng trong 15 giây...")
    print("👉 Hãy thử click mở cửa sổ ứng dụng bị đóng băng lên, nó sẽ tự thức dậy!")
    
    time.sleep(15)
    freezer.unfreeze_apps()