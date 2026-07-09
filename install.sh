#!/bin/bash

# ====================================================================
# BRAINGRAM AI - AUTO INSTALLER & DEPLOYMENT SCRIPT v8.0 (Dual-Core)
# Kết hợp cài đặt môi trường, phong ấn xung đột & tạo giao diện
# ====================================================================

echo "🚀 BẮT ĐẦU CÀI ĐẶT BRAINGRAM AI CYBERNETIC SYSTEM..."
echo "--------------------------------------------------------"

# 1. Lấy đường dẫn thư mục hiện tại tự động
CURRENT_DIR=$(pwd)
echo "📂 Thư mục gốc được xác nhận tại: $CURRENT_DIR"

# ====================================================================
# PHẦN 1: CÀI ĐẶT THƯ VIỆN HỆ THỐNG CẤP THẤP
# ====================================================================
echo "🔍 [1/5] Đang nhận diện hệ điều hành và nạp thư viện lõi..."

command_exists() { command -v "$1" >/dev/null 2>&1; }

if command_exists apt; then
    echo "   🐧 Hệ thống nhận diện: Debian/Ubuntu/Zorin."
    sudo apt update
    sudo apt install -y python3-psutil python3-venv xdotool
elif command_exists pacman; then
    echo "   🐉 Hệ thống nhận diện: Arch Linux/Garuda."
    sudo pacman -S --noconfirm python-psutil python-virtualenv xdotool
elif command_exists dnf; then
    echo "   🎩 Hệ thống nhận diện: Fedora/RedHat."
    sudo dnf install -y python3-psutil python3-virtualenv xdotool
else
    echo "   ⚠️ Cài đặt qua PIP..."
    python3 -m pip install psutil
fi

# ====================================================================
# PHẦN 2: DỌN DẸP XUNG ĐỘT QUYỀN LỰC (ĐỘC QUYỀN ĐIỀU KHIỂN)
# ====================================================================
echo "🛡️ [2/5] Đang phong ấn các trình quản lý năng lượng mặc định..."

CONFLICTING_SERVICES=("power-profiles-daemon.service" "tlp.service" "auto-cpufreq.service" "system76-power.service")
for service in "${CONFLICTING_SERVICES[@]}"; do
    if systemctl list-unit-files | grep -q "$service"; then
        sudo systemctl disable --now "$service" >/dev/null 2>&1
        sudo systemctl mask "$service" >/dev/null 2>&1
        echo "   ✅ Đã phong ấn thành công $service!"
    fi
done

# ====================================================================
# PHẦN 3: CẤU HÌNH MÔI TRƯỜNG ẢO CHO GIAO DIỆN (GUI)
# ====================================================================
echo "📦 [3/5] Đang cấu hình Môi trường ảo cho Dashboard..."
if [ ! -d "gui_env" ]; then
    python3 -m venv gui_env
fi

echo "   ⚙️ Đang nạp thư viện PyQt6..."
$CURRENT_DIR/gui_env/bin/pip install --upgrade pip > /dev/null 2>&1
$CURRENT_DIR/gui_env/bin/pip install PyQt6 > /dev/null 2>&1

# ====================================================================
# PHẦN 4: TẠO GIÁP BẤT TỬ (DUAL SYSTEMD DAEMONS)
# ====================================================================
echo "🤖 [4/5] Đang cấy Bộ não AI (Dual-Core) vào nhân Linux..."

# 4.1. Dịch vụ Cơ bắp (Watchdog)
sudo bash -c "cat > /etc/systemd/system/braingram_executor.service" <<EOL
[Unit]
Description=BrainGram AI - Hardware Executor (Watchdog)
After=multi-user.target

[Service]
Type=simple
User=root
WorkingDirectory=$CURRENT_DIR
ExecStart=/usr/bin/python3 $CURRENT_DIR/main_optimizer.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOL

# 4.2. Dịch vụ Bộ não (Q-Learning)
sudo bash -c "cat > /etc/systemd/system/braingram_ai.service" <<EOL
[Unit]
Description=BrainGram AI - Core Engine (Q-Learning)
After=multi-user.target

[Service]
Type=simple
User=root
WorkingDirectory=$CURRENT_DIR
ExecStart=/usr/bin/python3 $CURRENT_DIR/BrainAI.py
Restart=always
RestartSec=5
Nice=-5

[Install]
WantedBy=multi-user.target
EOL

echo "   🔄 Đang khởi động cấu trúc Systemd..."
sudo systemctl daemon-reload
sudo systemctl enable --now braingram_executor.service
sudo systemctl enable --now braingram_ai.service

# ====================================================================
# PHẦN 5: TẠO SHORTCUT ỨNG DỤNG CHO DASHBOARD
# ====================================================================
echo "🖥️ [5/5] Đang tạo Icon ứng dụng ra Menu Hệ thống..."
DESKTOP_FILE="$HOME/.local/share/applications/BrainGram.desktop"

cat > "$DESKTOP_FILE" <<EOL
[Desktop Entry]
Version=1.0
Type=Application
Name=BrainGram AI Dashboard
Comment=Hệ thống AI Điều phối Phần cứng
Exec=$CURRENT_DIR/gui_env/bin/python3 $CURRENT_DIR/brain_gui.py
Icon=applications-science
Terminal=false
Categories=System;Utility;
EOL

chmod +x "$DESKTOP_FILE"
cp "$DESKTOP_FILE" "$HOME/Desktop/" 2>/dev/null || true

echo "--------------------------------------------------------"
echo "🎉 HOÀN TẤT ĐÓNG GÓI VÀ CÀI ĐẶT!"
echo "👉 Cỗ máy 3 Lõi đang chạy ngầm bằng quyền Root."
echo "👉 Hãy bấm phím Windows, gõ 'BrainGram' để mở Bảng điều khiển (GUI)!"