#!/usr/bin/env python3
import os
import sys
import csv
import subprocess
import gc
from collections import deque

from PyQt6.QtCore import QTimer, Qt, QPointF, QRect, QThread, pyqtSignal
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QGridLayout, QFrame, 
                             QProgressBar, QSystemTrayIcon, QMenu, QTableWidget, 
                             QTableWidgetItem, QTabWidget, QTextEdit, QHeaderView,
                             QSlider, QSpinBox, QMessageBox)
from PyQt6.QtGui import QFont, QColor, QPainter, QPen, QIcon, QAction, QBrush

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "user_habit_log.csv")
BRAIN_COMMAND_FILE = os.path.join(BASE_DIR, ".brain_command")
CONFIG_FILE = os.path.join(BASE_DIR, "brain_config.ini")

# TỐI ƯU: Đã giảm xuống còn 3 Mode thiết thực nhất
ACTIONS = [
    "1. ECO MODE", 
    "2. BALANCE MODE", 
    "3. PERFORMANCE MODE"
]

class BrainDataWorker(QThread):
    data_received = pyqtSignal(list)

    def run(self):
        while True:
            if os.path.exists(LOG_FILE):
                try:
                    # Thuật toán lấy dòng cuối nhanh không ngốn RAM
                    with open(LOG_FILE, "r", encoding="utf-8") as f:
                        last_line = deque(f, maxlen=1)
                        if last_line:
                            reader = list(csv.reader(last_line))
                            if reader:
                                self.data_received.emit(reader[0]) 
                except Exception:
                    pass
            self.msleep(1500) # Đã tối ưu lên 1.5s để giảm tải ổ cứng

class RealtimeSparkline(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data_points = [0.0] * 300
        self.setMinimumHeight(50)
        
    def add_value(self, val):
        self.data_points.pop(0)
        self.data_points.append(val)
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        width, height = self.width(), self.height()
        painter.fillRect(0, 0, width, height, QColor("#111115"))
        
        max_val = max(self.data_points) if max(self.data_points) > 0 else 15.0
        if max_val < 5.0: max_val = 5.0
        
        points = []
        x_step = width / (max(len(self.data_points) - 1, 1))
        for i, val in enumerate(self.data_points):
            x = i * x_step
            y = height - ((val / max_val) * (height - 10)) - 5
            points.append(QPointF(x, y))
            
        pen = QPen(QColor("#2ECC71"), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        for i in range(len(points) - 1):
            painter.drawLine(points[i], points[i+1])

class NeuralGaugeMeter(QWidget):
    def __init__(self, label_text="Tốc độ học AI", parent=None):
        super().__init__(parent)
        self.label_text = label_text
        self.value = 0.0
        self.setMinimumSize(130, 100)
        
    def set_value(self, val):
        self.value = max(0.0, min(100.0, val))
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        
        painter.fillRect(0, 0, w, h, QColor("#131317"))
        
        pen_bg = QPen(QColor("#25252D"), 8)
        painter.setPen(pen_bg)
        painter.drawArc(15, 15, w-30, h-10, -30 * 16, 240 * 16)
        
        if self.value < 40: color = QColor("#2ECC71")
        elif self.value < 75: color = QColor("#E67E22")
        else: color = QColor("#E74C3C")
        
        pen_val = QPen(color, 8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_val)
        span_angle = int((self.value / 100.0) * 240)
        painter.drawArc(15, 15, w-30, h-10, 210 * 16, -span_angle * 16)
        
        painter.setPen(QPen(QColor("#FFFFFF")))
        painter.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        painter.drawText(QRect(0, 35, w, 25), Qt.AlignmentFlag.AlignCenter, f"{self.value:.1f}%")
        
        painter.setPen(QPen(QColor("#888892")))
        painter.setFont(QFont("Arial", 8))
        painter.drawText(QRect(0, 65, w, 20), Qt.AlignmentFlag.AlignCenter, self.label_text)

class AICognitiveChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(140)
        self.stats = {act: 0 for act in ACTIONS}
        
    def set_stats_data(self, stats_data):
        self.stats = stats_data
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        painter.fillRect(0, 0, w, h, QColor("#16161A"))
        
        max_count = max(self.stats.values()) if max(self.stats.values()) > 0 else 1
        padding_left, padding_bottom = 40, 25
        chart_w, chart_h = w - padding_left - 20, h - padding_bottom - 20
        
        num_bars = len(ACTIONS)
        bar_gap = 25 
        bar_w = (chart_w - (bar_gap * (num_bars - 1))) / max(num_bars, 1)
        
        painter.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        for i, action in enumerate(ACTIONS):
            count = self.stats.get(action, 0)
            bx = padding_left + i * (bar_w + bar_gap)
            bar_height_pixels = (count / max_count) * chart_h
            by = h - padding_bottom - bar_height_pixels
            
            if count > 0:
                painter.setPen(Qt.PenStyle.NoPen)
                colors = ["#2ECC71", "#3498DB", "#E74C3C"]
                painter.setBrush(QBrush(QColor(colors[i % 3])))
                painter.drawRect(QRect(int(bx), int(by), int(bar_w), int(bar_height_pixels)))
            else:
                painter.setPen(QPen(QColor("#2C2C35"), 1, Qt.PenStyle.DashLine))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(QRect(int(bx), int(h - padding_bottom - 5), int(bar_w), 5))
                
            painter.setPen(QPen(QColor("#FFFFFF")))
            painter.drawText(QRect(int(bx), int(by - 15), int(bar_w), 15), Qt.AlignmentFlag.AlignCenter, str(count))
            painter.setPen(QPen(QColor("#888892")))
            short_name = action.split(". ")[1] if ". " in action else action
            painter.drawText(QRect(int(bx), int(h - padding_bottom + 4), int(bar_w), 20), Qt.AlignmentFlag.AlignCenter, short_name)

class BrainGramDashboardV72(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BrainGram AI Cybernetic System v7.2-Final")
        self.setMinimumSize(960, 720)
        self.is_quitting = False
        
        self.setStyleSheet("""
            QMainWindow { background-color: #0B0B0D; }
            QTabWidget::panel { border: 1px solid #1F1F24; background: #131317; border-radius: 8px; }
            QTabWidget QWidget { background-color: #131317; }
            QTabBar::tab { background: #1A1A1F; color: #888892; padding: 10px 25px; font-weight: bold; font-size: 13px; border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 4px; border: 1px solid #1F1F24; }
            QTabBar::tab:selected { background: #131317; color: #3498DB; border-bottom: 2px solid #3498DB; }
            QLabel { color: #E2E2E6; font-family: 'Segoe UI', Arial, sans-serif; background: transparent; }
            QFrame#Card { background-color: #1A1A22; border-radius: 12px; border: 1px solid #25252D; }
            QProgressBar { border: 1px solid #2C2C35; border-radius: 6px; background-color: #17171C; text-align: center; color: white; font-weight: bold; }
            QProgressBar::chunk { border-radius: 5px; background-color: #27AE60; }
            QPushButton { background-color: #1A1A1F; color: #A0A0AA; border-radius: 8px; border: 1px solid #25252D; padding: 11px; font-size: 13px; font-weight: bold; }
            QPushButton:hover { background-color: #24242B; color: #FFFFFF; border: 1px solid #3E3E4A; }
            QPushButton#ActiveAction { background-color: #0E5A30; color: #2ECC71; border: 2px solid #2ECC71; }
            QPushButton#AIControlBtn { background-color: #152233; color: #3498DB; border: 1px solid #244263; font-size: 13px; }
            QPushButton#AIControlActive { background-color: #132D4B; color: #5DADE2; border: 2px solid #5DADE2; font-weight: bold; }
            QPushButton#DangerBtn { background-color: #2A1A1A; color: #E74C3C; border: 1px solid #5C2424; }
            QPushButton#DangerBtn:hover { background-color: #441F1F; color: #FFFFFF; }
            QTableWidget { background-color: #16161A; border: 1px solid #2C2C35; color: #E2E2E6; gridline-color: #2C2C35; }
            QHeaderView::section { background-color: #22222A; color: #3498DB; font-weight: bold; border: 1px solid #1A1A1F; padding: 6px; }
            QTextEdit { background-color: #16161A; border: 1px solid #23232A; border-radius: 8px; color: #E2E2E6; padding: 8px; font-size: 12px; }
            QSlider::groove:horizontal { border: 1px solid #2C2C35; height: 6px; background: #1A1A22; border-radius: 3px; }
            QSlider::handle:horizontal { background: #3498DB; width: 14px; margin: -4px 0; border-radius: 7px; }
            QSpinBox { background-color: #1A1A22; color: #FFFFFF; border: 1px solid #2C2C35; border-radius: 4px; padding: 3px; }
        """)
        
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)
        
        self.init_tab_dashboard()
        self.init_tab_brain_analytics()
        self.init_tab_config_management()
        
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon.fromTheme("applications-science"))
        tray_menu = QMenu()
        open_action = QAction("Mở Hệ Thống", self)
        open_action.triggered.connect(self.showNormal)
        quit_action = QAction("Thoát Ứng Dụng", self)
        quit_action.triggered.connect(self.actual_quit)
        tray_menu.addAction(open_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
        # BƯỚC NÂNG CẤP LÕI: Gom hết về 1 luồng Worker, bỏ QTimer
        self.worker = BrainDataWorker()
        self.worker.data_received.connect(self.orchestrate_data_stream)
        self.worker.start()
        
        self.orchestrate_data_stream() # Khởi chạy lần đầu
        
    def init_tab_dashboard(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        header_layout = QHBoxLayout()
        title_label = QLabel("⚡ BrainGram AI Cybernetic Dashboard")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #3498DB;")
        header_layout.addWidget(title_label)
        
        self.status_label = QLabel("Trạng thái: Đang kết nối...")
        self.status_label.setStyleSheet("color: #A0A0AA;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        header_layout.addWidget(self.status_label)
        layout.addLayout(header_layout)
        
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)
        
        self.card_battery = QFrame()
        self.card_battery.setObjectName("Card")
        b_box = QVBoxLayout(self.card_battery)
        lbl_b = QLabel("🔋 PIN HỆ THỐNG & ĐỒNG HỒ TTE")
        lbl_b.setStyleSheet("color: #F1C40F; font-weight: bold; font-size: 11px;")
        b_box.addWidget(lbl_b)
        self.pbar_battery = QProgressBar()
        b_box.addWidget(self.pbar_battery)
        self.lbl_bat_health = QLabel("Sức khỏe thực tế: Tốt")
        self.lbl_bat_health.setStyleSheet("color: #888892; font-size: 11px;")
        self.lbl_tte = QLabel("Tính toán thời gian...")
        self.lbl_tte.setStyleSheet("color: #F1C40F; font-size: 11px;")
        b_box.addWidget(self.lbl_bat_health)
        b_box.addWidget(self.lbl_tte)
        cards_layout.addWidget(self.card_battery)
        
        self.card_chrome = QFrame()
        self.card_chrome.setObjectName("Card")
        c_box = QVBoxLayout(self.card_chrome)
        lbl_c = QLabel("🌐 GIÁM SÁT ỨNG DỤNG ĐỈNH HỆ THỐNG")
        lbl_c.setStyleSheet("color: #E67E22; font-weight: bold; font-size: 11px;")
        c_box.addWidget(lbl_c)
        self.lbl_chrome_app = QLabel("Đang nhận diện...")
        self.lbl_chrome_app.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.lbl_chrome_cpu = QLabel("Tải: 0.0% CPU")
        self.lbl_chrome_cpu.setStyleSheet("color: #888892; font-size: 11px;")
        c_box.addWidget(self.lbl_chrome_app)
        c_box.addWidget(self.lbl_chrome_cpu)
        cards_layout.addWidget(self.card_chrome)
        
        self.card_temp = QFrame()
        self.card_temp.setObjectName("Card")
        t_box = QVBoxLayout(self.card_temp)
        lbl_t = QLabel("🌡️ NHIỆT ĐỘ & ĐỒ THỊ ĐIỆN NĂNG")
        lbl_t.setStyleSheet("color: #E74C3C; font-weight: bold; font-size: 11px;")
        t_box.addWidget(lbl_t)
        th_box = QHBoxLayout()
        v_box = QVBoxLayout()
        self.lbl_temp_val = QLabel("0.0 °C")
        self.lbl_temp_val.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        self.lbl_watt_val = QLabel("0.00 W")
        self.lbl_watt_val.setStyleSheet("color: #2ECC71; font-weight: bold; font-size: 11px;")
        v_box.addWidget(self.lbl_temp_val)
        v_box.addWidget(self.lbl_watt_val)
        th_box.addLayout(v_box)
        self.sparkline = RealtimeSparkline()
        th_box.addWidget(self.sparkline, stretch=1)
        t_box.addLayout(th_box)
        cards_layout.addWidget(self.card_temp)
        
        layout.addLayout(cards_layout)
        
        self.btn_ai_mode = QPushButton("🤖 TRẢ QUYỀN CHO AI (Bật Chế Độ Tự ĐỘng Học)")
        self.btn_ai_mode.setObjectName("AIControlBtn")
        self.btn_ai_mode.clicked.connect(self.enable_ai_mode)
        layout.addWidget(self.btn_ai_mode)
        
        control_title = QLabel("🛠️ Bảng điều khiển Profile phần cứng (Bấm nút để ép chế độ)")
        control_title.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        control_title.setStyleSheet("color: #888892;")
        layout.addWidget(control_title)
        
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(10)
        self.buttons = {}
        positions = [(0, 0), (0, 1), (0, 2)]
        for position, action_name in zip(positions, ACTIONS):
            btn = QPushButton(action_name)
            btn.clicked.connect(lambda checked, name=action_name: self.override_mode(name))
            self.grid_layout.addWidget(btn, *position)
            self.buttons[action_name] = btn
        layout.addLayout(self.grid_layout)
        
        self.tab_widget.addTab(widget, "⚡ Bảng Điều Khiển")

    def init_tab_brain_analytics(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        top_analysis_layout = QHBoxLayout()
        
        chart_vbox = QVBoxLayout()
        lbl_ch = QLabel("📊 TẦN SUẤT BỘ NÃO AI TỰ ĐIỀU PHỐI PROFILE")
        lbl_ch.setStyleSheet("color: #2ECC71; font-weight: bold;")
        chart_vbox.addWidget(lbl_ch)
        self.cognitive_chart = AICognitiveChart()
        chart_vbox.addWidget(self.cognitive_chart)
        top_analysis_layout.addLayout(chart_vbox, stretch=3)
        
        gauges_hbox = QHBoxLayout()
        self.gauge_learning = NeuralGaugeMeter("Tốc Độ Học AI")
        self.gauge_entropy = NeuralGaugeMeter("Độ Phân Vân Não")
        gauges_hbox.addWidget(self.gauge_learning)
        gauges_hbox.addWidget(self.gauge_entropy)
        
        gauge_vbox = QVBoxLayout()
        lbl_g = QLabel("🧠 TRẠNG THÁI XUNG THẦN KINH")
        lbl_g.setStyleSheet("color: #3498DB; font-weight: bold;")
        gauge_vbox.addWidget(lbl_g)
        gauge_vbox.addLayout(gauges_hbox)
        top_analysis_layout.addLayout(gauge_vbox, stretch=2)
        
        layout.addLayout(top_analysis_layout)
        
        lbl_ins = QLabel("📝 BÁO CÁO NHẬN THỨC VÀ LỜI KHUYÊN TỪ TRỢ LÝ BRAINGRAM")
        lbl_ins.setStyleSheet("color: #E67E22; font-weight: bold;")
        layout.addWidget(lbl_ins)
        self.txt_ai_insights = QTextEdit()
        self.txt_ai_insights.setReadOnly(True)
        self.txt_ai_insights.setMaximumHeight(70)
        layout.addWidget(self.txt_ai_insights)
        
        lbl_ma = QLabel("📋 DANH SÁCH LỊCH SỬ MA TRẬN KÝ ỨC GẦN NHẤT")
        lbl_ma.setStyleSheet("color: #9B59B6; font-weight: bold;")
        layout.addWidget(lbl_ma)
        
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Mốc thời gian", "Trạng thái sạc", "Mức Pin", "Nhiệt độ", "Ứng dụng đỉnh"])
        
        try:
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        except AttributeError:
            try:
                self.table.horizontalHeader().setSectionResizeMode(QHeaderView.SectionResizeMode.Stretch)
            except: pass
                
        layout.addWidget(self.table)
        self.tab_widget.addTab(widget, "🧠 Phân Tích Não Bộ AI")

    def init_tab_config_management(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        daemon_frame = QFrame()
        daemon_frame.setStyleSheet("background-color: #1A1A22; border-radius: 10px; border: 1px solid #2C2C35;")
        df_layout = QVBoxLayout(daemon_frame)
        
        lbl_d_title = QLabel("⚙️ QUẢN LÝ DỊCH VỤ NỀN CORE DAEMON")
        lbl_d_title.setStyleSheet("color: #3498DB; font-weight: bold; font-size: 12px; border: none;")
        df_layout.addWidget(lbl_d_title)
        
        btn_hbox = QHBoxLayout()
        self.btn_daemon_status = QPushButton("⏳ Đang kiểm tra Core Service...")
        self.btn_daemon_status.clicked.connect(self.check_daemon_service)
        
        btn_daemon_restart = QPushButton("🔄 Restart Dịch Vụ Ngầm")
        btn_daemon_restart.setStyleSheet("color: #F1C40F; border-color: #A48518;")
        btn_daemon_restart.clicked.connect(lambda: self.trigger_daemon_command("restart"))
        
        btn_daemon_stop = QPushButton("🛑 Dừng Dịch Vụ AI")
        btn_daemon_stop.setObjectName("DangerBtn")
        btn_daemon_stop.clicked.connect(lambda: self.trigger_daemon_command("stop"))
        
        btn_hbox.addWidget(self.btn_daemon_status)
        btn_hbox.addWidget(btn_daemon_restart)
        btn_hbox.addWidget(btn_daemon_stop)
        df_layout.addLayout(btn_hbox)
        layout.addWidget(daemon_frame)
        
        maint_frame = QFrame()
        maint_frame.setStyleSheet("background-color: #1A1A22; border-radius: 10px; border: 1px solid #2C2C35;")
        mf_layout = QVBoxLayout(maint_frame)
        
        lbl_m_title = QLabel("🧹 HỆ THỐNG BẢO TRÌ MA TRẬN BỘ NHỚ")
        lbl_m_title.setStyleSheet("color: #9B59B6; font-weight: bold; font-size: 12px; border: none;")
        mf_layout.addWidget(lbl_m_title)
        
        maint_hbox = QHBoxLayout()
        btn_clear_log = QPushButton("🗑️ Xóa sạch bộ nhớ Log đệm (Reset CSV)")
        btn_clear_log.setObjectName("DangerBtn")
        btn_clear_log.clicked.connect(self.clear_log_history)
        
        btn_ram_flush = QPushButton("⚡ Ép xung & Giải phóng bộ nhớ đệm GUI")
        btn_ram_flush.clicked.connect(self.flush_gui_ram)
        
        maint_hbox.addWidget(btn_clear_log)
        maint_hbox.addWidget(btn_ram_flush)
        mf_layout.addLayout(maint_hbox)
        layout.addWidget(maint_frame)
        
        layout.addStretch()
        self.tab_widget.addTab(widget, "⚙️ Cấu Hình & Quản Trị Core")

    # BƯỚC NÂNG CẤP LÕI: Thêm *args để nhận tín hiệu mà không bị crash
    def orchestrate_data_stream(self, *args):
        self.check_daemon_service()

        if not os.path.exists(LOG_FILE): 
            return
        try:
            # Chỉ đọc file 1 lần duy nhất để lấy 30 dòng
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                lines = list(deque(f, maxlen=30))
                
            if len(lines) <= 1: 
                return
            
            reader = list(csv.reader(lines))
            row = reader[-1]
            
            if len(row) >= 10:
                power = row[2]
                try: watt = float(row[3])
                except: watt = 0.0
                try: battery = int(row[4])
                except: battery = 100
                temp = row[6]
                top_app = row[8]
                app_cpu = row[9]
                
                self.sparkline.add_value(watt)
                self.pbar_battery.setValue(battery)
                self.pbar_battery.setFormat(f"{battery}% ({power})")
                
                if "BATTERY" in power.upper() and watt > 1.5:
                    hours_left = ((72.0 * battery) / 100.0) / watt
                    m_total = int(hours_left * 60)
                    self.lbl_tte.setText(f"Dự kiến còn: {m_total // 60} giờ {m_total % 60} phút")
                else:
                    self.lbl_tte.setText("Trạng thái nguồn: Đang sạc / AC Mode")
                    
                self.lbl_chrome_app.setText(f"🌐 CHROME (ĐANG HỌC TẬP)" if "CHROME" in top_app.upper() else f"📦 {top_app.upper()}")
                self.lbl_chrome_cpu.setText(f"Tải ứng dụng: {app_cpu}% CPU")
                self.lbl_temp_val.setText(f"{temp} °C")
                self.lbl_watt_val.setText(f"Dòng xả: {watt:.2f} W")
                
                valid_data = []
                stats_counter = {act: 0 for act in ACTIONS}
                
                for r_line in reader:
                    if r_line and len(r_line) >= 10:
                        valid_data.append(r_line)
                        log_str = "".join(r_line).upper()
                        for act in ACTIONS:
                            if act.split(". ")[1].upper() in log_str:
                                stats_counter[act] += 1
                                
                self.cognitive_chart.set_stats_data(stats_counter)
                
                try:
                    cpu_float = float(app_cpu)
                    self.gauge_learning.set_value(min(98.5, 25.0 + (cpu_float * 0.6)))
                    self.gauge_entropy.set_value(min(95.0, 10.0 + (watt * 4.5)))
                except: pass
                
                most_used_profile = max(stats_counter, key=stats_counter.get)
                insight_text = (
                    f"🤖 [TRỢ LÝ BRAINGRAM]: AI đã chuyển sang chế độ 3 Lõi Thông Minh.\n"
                    f"• Profile phân phối hiệu suất ưu tiên: '{most_used_profile}'.\n"
                    f"• Hệ thống duy trì nhiệt độ {temp}°C."
                )
                self.txt_ai_insights.setPlainText(insight_text)
                
                display_rows = valid_data[-20:]
                self.table.setRowCount(len(display_rows))
                for r_idx, r in enumerate(reversed(display_rows)):
                    self.table.setItem(r_idx, 0, QTableWidgetItem(str(r[0])))
                    self.table.setItem(r_idx, 1, QTableWidgetItem(str(r[2])))
                    self.table.setItem(r_idx, 2, QTableWidgetItem(f"{r[4]}%"))
                    self.table.setItem(r_idx, 3, QTableWidgetItem(f"{r[6]} °C"))
                    self.table.setItem(r_idx, 4, QTableWidgetItem(str(r[8]).upper()))
        except Exception:
            pass
            
        if os.path.exists(BRAIN_COMMAND_FILE):
            try:
                with open(BRAIN_COMMAND_FILE, "r") as f:
                    current_active = f.read().strip()
                for act, btn in self.buttons.items():
                    if act == current_active: btn.setObjectName("ActiveAction")
                    else: btn.setObjectName("")
                    btn.setStyle(btn.style())
                self.btn_ai_mode.setObjectName("AIControlActive")
                self.btn_ai_mode.setText("🤖 AI AUTO MODE (Bộ não đang tự điều phối tối ưu)")
                self.btn_ai_mode.setStyle(self.btn_ai_mode.style())
                self.status_label.setText(f"Chế độ hiện tại: <font color='#2ECC71'><b>{current_active}</b></font>")
            except Exception: pass

    def override_mode(self, action_name):
        try:
            with open(BRAIN_COMMAND_FILE, "w") as f: f.write(action_name)
            self.btn_ai_mode.setObjectName("AIControlBtn")
            self.btn_ai_mode.setText("🤖 TRẢ QUYỀN CHO AI (Bật Chế Độ Tự ĐỘng Học)")
            self.btn_ai_mode.setStyle(self.btn_ai_mode.style())
            self.orchestrate_data_stream()
        except Exception: pass

    def enable_ai_mode(self):
        try:
            self.btn_ai_mode.setObjectName("AIControlActive")
            self.btn_ai_mode.setText("🤖 AI AUTO MODE (Bộ não đang tự điều phối tối ưu)")
            self.btn_ai_mode.setStyle(self.btn_ai_mode.style())
            self.status_label.setText("Chế độ hiện tại: <font color='#3498DB'><b>AI đang tính toán...</b></font>")
            if os.path.exists(BRAIN_COMMAND_FILE):
                os.remove(BRAIN_COMMAND_FILE)
        except Exception: pass

    def check_daemon_service(self):
        try:
            res = subprocess.run(["pgrep", "-f", "zorin_brain.py"], capture_output=True, text=True)
            if res.stdout.strip():
                self.btn_daemon_status.setText("🟢 Core Daemon: ĐANG CHẠY")
                self.btn_daemon_status.setStyleSheet("background-color: #112A18; color: #2ECC71; font-weight: bold; border-color: #1F4D2B;")
            else:
                self.btn_daemon_status.setText("🔴 Core Daemon: ĐÃ DỪNG")
                self.btn_daemon_status.setStyleSheet("background-color: #2A1111; color: #E74C3C; font-weight: bold; border-color: #5C1F1F;")
        except Exception:
            self.btn_daemon_status.setText("⚠️ Không thể check dịch vụ")

    def trigger_daemon_command(self, action):
        python_exec = os.path.join(BASE_DIR, "gui_env/bin/python3")
        daemon_script = os.path.join(BASE_DIR, "zorin_brain.py")
        
        if action == "stop":
            subprocess.run(["pkill", "-f", "zorin_brain.py"])
            QMessageBox.information(self, "BrainGram AI Core", "Đã gửi tín hiệu dừng tiến trình nền Core Daemon!")
        elif action == "restart":
            subprocess.run(["pkill", "-f", "zorin_brain.py"])
            os.system(f"nohup {python_exec} {daemon_script} > /dev/null 2>&1 &")
            QMessageBox.information(self, "BrainGram AI Core", "Dịch vụ nền AI Daemon đã được khởi động lại!")
        self.check_daemon_service()

    def clear_log_history(self):
        reply = QMessageBox.question(self, "Xác nhận xóa ký ức", "Bạn có chắc chắn muốn dọn sạch lịch sử CSV không?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                with open(LOG_FILE, "w", encoding="utf-8") as f:
                    f.write("Timestamp,Mode,PowerState,Wattage,BatteryPct,BatteryHealth,Temp,Governor,TopApp,AppCPU\n")
                self.table.setRowCount(0)
            except Exception: pass

    def flush_gui_ram(self):
        gc.collect()
        QMessageBox.information(self, "Xung Thần Kinh", "Đã dọn sạch RAM rác, ép luồng vẽ đồ thị tối ưu mượt mà!")

    def closeEvent(self, event):
        if not self.is_quitting:
            event.ignore()
            self.hide()
        else: 
            event.accept()

    def actual_quit(self):
        self.is_quitting = True
        self.close()
        QApplication.quit()

if __name__ == "__main__":
    print("1. Bắt đầu khởi chạy hệ thống...")
    app = QApplication(sys.argv)
    print("2. Đang nạp Ma trận Giao diện...")
    window = BrainGramDashboardV72()
    print("3. Đang xuất ảnh lên màn hình KDE Plasma...")
    window.show()
    print("4. Đã hiển thị thành công! Vòng lặp kích hoạt.")
    sys.exit(app.exec())