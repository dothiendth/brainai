# 🧠 BrainGram AI Cybernetic System v8.0-Final (Dual-Core)

**BrainGram AI** là một hệ thống tự động hóa và điều phối phần cứng thông minh dành cho Linux (tối ưu hóa cho Garuda, Arch, Zorin OS, KDE Plasma). 
Thay vì để hệ điều hành quản lý điện năng một cách máy móc, BrainGram sử dụng thuật toán Học Tăng Cường (**Q-Learning**) để học hỏi thói quen người dùng, từ đó tự động bẻ lái các Profile phần cứng (ECO, BALANCE, PERFORMANCE) nhằm tối đa hóa thời lượng pin và bảo vệ linh kiện.

## ✨ 3 Trụ Cột Sức Mạnh (The 3 Cores)
* ❄️ **Smart Freezer (Đóng băng tiến trình):** Sử dụng "Mắt thần" theo dõi cửa sổ và lệnh `SIGSTOP` để đóng băng 100% CPU của các app ngầm (Discord, Zalo...) khi rút sạc, và rã đông tức thì trong 1 giây khi click vào.
* 🎛️ **P-State Manager (Điều phối vi mạch):** Giao tiếp trực tiếp với tính năng Hardware P-States (HWP) của CPU. Bung sức mạnh `performance` khi cắm sạc và ngủ đông sinh học `balance_power` khi chạy pin.
* 🔋 **Battery Protector (Bypass phần cứng):** Ghi đè vào chip điều khiển nguồn (EC), tự động ngắt sạc ở 80% và chuyển dòng điện đi thẳng vào bo mạch chủ để chống chai pin khi ngồi code.

## 🛠️ Kiến trúc Hệ thống Kép (Dual-Daemon)
1. `BrainAI.py`: Tiến trình Não bộ (Daemon) - Q-Learning, quản lý 3 Lõi, chạy dưới quyền Root (`Nice=-5`).
2. `main_optimizer.py`: Tiến trình Cơ bắp (Watchdog) - Tắt Turbo Boost, điều chỉnh điện áp WiFi/Audio.
3. `brain_gui.py`: Giao diện Dashboard (Mắt nhìn và tương tác) chạy qua môi trường ảo PyQt6.
4. `install.sh`: Kịch bản Auto-Installer Tự động hóa 100%.

## 🚀 Cài đặt Nhanh (Auto-Deploy)
Hệ thống tự động nhận diện Distro (Ubuntu/Arch/Fedora), cài thư viện và tạo icon ứng dụng.

chmod +x install.sh
./install.sh
---

## ⚠️ LƯU Ý ĐẶC BIỆT: VỀ QUYỀN ĐIỀU KHIỂN NĂNG LƯỢNG

Để BrainGram AI hoạt động độc quyền và không bị "đánh nhau" với các hệ thống cũ gây giật lag, file cài đặt đã **Tạm thời Phong ấn (Mask)** các trình quản lý năng lượng mặc định của hệ điều hành (ví dụ: `power-profiles-daemon`, `tlp`, `auto-cpufreq`).

Nếu sau này bạn muốn **GỠ BỎ** BrainGram AI và đưa máy tính về trạng thái "zin" gốc của nhà sản xuất, bạn **bắt buộc** phải giải trừ phong ấn bằng 2 lệnh sau:

**1. Xóa bỏ phong ấn (Unmask):**
sudo systemctl unmask power-profiles-daemon.service tlp.service auto-cpufreq.service system76-power.service

**2. Khởi động lại công cụ mặc định (Ví dụ với GNOME/KDE đời mới):**
sudo systemctl enable --now power-profiles-daemon.service