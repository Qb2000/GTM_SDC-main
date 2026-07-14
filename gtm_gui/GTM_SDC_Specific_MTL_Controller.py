from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
from GTM_SDC_specific_MTL import Ui_specific_MTL_window  
from GTM_SDC_specific_CMD_DAC_HV_setting_Controller import CmdDacHvSettingWindow
from datetime import datetime, timedelta
import numpy as np


# 極區緯度閾值（絕對值超過此值視為 polar region）
POLAR_LAT_THRESHOLD = 60.0


class SpecificMTLWindow(QtWidgets.QMainWindow):
    def __init__(self, main_controller=None):
        super().__init__()
        self.ui = Ui_specific_MTL_window()
        self.ui.setupUi(self)
        self.row_count = 0
        self.main_controller = main_controller  # 主視窗，用來取得 TLE 計算結果
        # 每個 row 的 CMD config 資料與視窗實例，key = row QWidget
        self._cmd_config_data = {}    # {row_widget: dict}
        self._cmd_config_windows = {} # {row_widget: CmdDacHvSettingWindow}
        self.setup()

    def setup(self):
        self.ui.Generate_specific_MTL.setEnabled(True)
        self.ui.Generate_specific_MTL.clicked.connect(self.generate)
        self.ui.verticalLayout.setAlignment(Qt.AlignTop)
        self.ui.add_row.clicked.connect(self.add_row_function)
        self.ui.remove_row.clicked.connect(self.remove_specific_row)
        self.ui.remove_row.setEnabled(False)
        self.ui.rowTemplateWidget.setVisible(False)  # 隱藏模板，不要顯示
        self.add_row_function()

    def add_row_function(self):
        sender = self.sender()
        # 新增一個 row（外層 QWidget + GridLayout）
        new_row = QtWidgets.QWidget()
        grid_layout = QtWidgets.QGridLayout(new_row)
        grid_layout.setContentsMargins(0, 0, 0, 0)

        # 複製所有 widget（照順序）
        def clone_label(origin):
            new = QtWidgets.QLabel()
            new.setText(origin.text())
            return new
        
        def clone_datetimeedit(origin):
            new = QtWidgets.QDateTimeEdit()
            new.setDateTime(origin.dateTime())
            return new

        def clone_checkbox(origin):
            new = QtWidgets.QCheckBox()
            new.setText(origin.text())
            new.setChecked(origin.isChecked())
            return new

        def clone_button(origin, text):
            new = QtWidgets.QPushButton(text)
            new.setEnabled(origin.isEnabled())
            return new

        # 複製每個 widget（依照 UI 的 col 順序）
        grid_layout.addWidget(clone_label(self.ui.label), 0, 0)

        use_timing_cb = clone_checkbox(self.ui.use_timming)
        grid_layout.addWidget(use_timing_cb, 0, 1)

        start_dt = clone_datetimeedit(self.ui.dateTimeEdit)
        end_dt   = clone_datetimeedit(self.ui.dateTimeEdit_2)
        grid_layout.addWidget(start_dt, 0, 2)
        grid_layout.addWidget(end_dt,   0, 3)

        saa_cb   = clone_checkbox(self.ui.SAA_power_on)
        polar_cb = clone_checkbox(self.ui.polar_region_power_on)
        sunlit_cb = clone_checkbox(self.ui.Sunlit_power_on)
        grid_layout.addWidget(saa_cb,    0, 4)
        grid_layout.addWidget(polar_cb,  0, 5)
        grid_layout.addWidget(sunlit_cb, 0, 6)

        grid_layout.addWidget(clone_button(self.ui.CMD_config, "CMD_config"), 0, 7)

        # use_timming 控制 dateTimeEdit 和 checkbox 的 enabled 狀態
        def _apply_timing_mode(checked, s=start_dt, e=end_dt,
                               saa=saa_cb, polar=polar_cb, sunlit=sunlit_cb):
            s.setEnabled(checked)
            e.setEnabled(checked)
            saa.setEnabled(not checked)
            polar.setEnabled(not checked)
            sunlit.setEnabled(not checked)

        # 初始狀態：未勾選 → dateTimeEdit disabled，checkbox enabled
        _apply_timing_mode(use_timing_cb.isChecked())
        use_timing_cb.stateChanged.connect(
            lambda state, fn=_apply_timing_mode: fn(state == Qt.Checked)
        )

        # CMD_config 按鈕連接到本 row 的設定視窗
        cmd_btn = grid_layout.itemAt(7).widget()
        # 為這個 row 建立獨立的 config_data dict
        config_data = {}
        self._cmd_config_data[new_row] = config_data
        cmd_btn.clicked.connect(lambda checked, rw=new_row: self._open_cmd_config(rw))

        # 加、減按鈕
        add_btn = clone_button(self.ui.add_row, "+")
        remove_btn = clone_button(self.ui.remove_row, "-")
        grid_layout.addWidget(add_btn, 0, 8)
        grid_layout.addWidget(remove_btn, 0, 9)

        # 按鈕連接功能（可動態控制）
        add_btn.clicked.connect(self.add_row_function)
        remove_btn.clicked.connect(lambda: self.remove_specific_row(new_row))
        
        
        # 插入指定位置
        if self.row_count > 0:
            for i in range(self.ui.verticalLayout.count()):
                item = self.ui.verticalLayout.itemAt(i).widget()
                if item.children()[0].layout().itemAt(8).widget() == sender:
                    index = item.children()[0].layout().itemAt(0).widget().text()[0]
                    break
            self.ui.verticalLayout.insertWidget(int(index)+1, new_row)
        else:
            self.ui.verticalLayout.addWidget(new_row)
            
        # for i in range(self.ui.verticalLayout.count()):    
        #     item = self.ui.verticalLayout.itemAt(i).widget()
        #     print(item.children()[0].layout().itemAt(0).widget())
        #     print(item.children()[0].layout().itemAt(1).widget())
        #     print(item.children()[0].layout().itemAt(2).widget())
        #     print(item.children()[0].layout().itemAt(3).widget())
        #     print(item.children()[0].layout().itemAt(4).widget())
        #     print(item.children()[0].layout().itemAt(5).widget())
        #     print(item.children()[0].layout().itemAt(6).widget())
        #     print(item.children()[0].layout().itemAt(7).widget())
            
        # 把這一行加到 verticalLayout 裡
        # self.ui.verticalLayout.addWidget(new_row)
        self.row_count += 1
        self.update_row_numbers()

    def _open_cmd_config(self, row_widget):
        """開啟（或重新顯示）對應 row 的 CMD DAC/HV 設定視窗。"""
        # 取得該 row 在 layout 中的序號作為標題
        row_index = -1
        for i in range(1, self.ui.verticalLayout.count()):
            if self.ui.verticalLayout.itemAt(i).widget() == row_widget:
                row_index = i
                break

        config_data = self._cmd_config_data.get(row_widget, {})

        # 若視窗已存在且未關閉，直接帶到前景
        win = self._cmd_config_windows.get(row_widget)
        if win is not None and not win.isHidden():
            win.raise_()
            win.activateWindow()
            return

        win = CmdDacHvSettingWindow(config_data, row_index)
        self._cmd_config_windows[row_widget] = win
        win.show()

    def remove_specific_row(self, row_widget):
        # 關閉並清理對應的 CMD config 視窗與資料
        win = self._cmd_config_windows.pop(row_widget, None)
        if win is not None:
            win.close()
        self._cmd_config_data.pop(row_widget, None)

        # 從 layout 中移除 row，然後刪除
        self.ui.verticalLayout.removeWidget(row_widget)
        row_widget.deleteLater()
        self.row_count -= 1
        self.update_row_numbers()
        if self.row_count == 1:
           row_widget = self.ui.verticalLayout.itemAt(1).widget()
           remove_botton = row_widget.children()[0].layout().itemAt(9).widget()
           remove_botton.setEnabled(False)
  
    def update_row_numbers(self):
        for i in range(1,self.ui.verticalLayout.count()):
            row_widget = self.ui.verticalLayout.itemAt(i).widget()
            if row_widget:
                number_label = row_widget.children()[0].layout().itemAt(0).widget()
                number_label.setText(f"{i}.")
                remove_botton = row_widget.children()[0].layout().itemAt(9).widget()
                if self.row_count > 1:
                    remove_botton.setEnabled(True)             
                 

    def generate(self): #default generate
        from GTM_SDC_UI_Controller_Mtl_Cmd import UiMtlCmd
        from GTM_SDC_UI_Controller_Mtl_Cmd_Backend import (
            load_tle, calculate_orbit_eclipse, circle_saa, in_saa
        )

        self.gen = UiMtlCmd()

        # 從主視窗取得計算起點 UTC（與 mtl_generate 邏輯一致）
        mc = self.main_controller
        if mc is not None and hasattr(mc, 'start_time_flag'):
            if mc.start_time_flag == 1:
                self.gen.mtl_start_utc = datetime.utcnow()
            elif mc.start_time_flag == 2:
                self.gen.mtl_start_utc = datetime.strptime(mc.assign_utc, '%Y-%m-%d %H:%M:%S')
            else:
                self.gen.mtl_start_utc = datetime.utcnow()
        else:
            self.gen.mtl_start_utc = datetime.utcnow()

        # 計算整段時間的軌道資料（若主視窗已有 TLE 檔案路徑則重新計算）
        has_tle = mc is not None and hasattr(mc, 'mtl_input_file') and bool(getattr(mc, 'mtl_input_file', ''))

        if has_tle:
            # total_mins 從主視窗的 period 設定取，與 mtl_generate 一致
            if hasattr(mc, 'period_mins') and mc.period_mins:
                total_mins = mc.period_mins
            elif hasattr(mc, 'period_flag'):
                if mc.period_flag == 1:
                    total_mins = int(mc.mtl_orbits) * 90
                elif mc.period_flag == 2:
                    total_mins = int(mc.mtl_days) * 24 * 60
                elif mc.period_flag == 3:
                    total_mins = int(mc.mtl_hours) * 60
                elif mc.period_flag == 4:
                    total_mins = int(mc.mtl_minutes)
                else:
                    total_mins = 90
            else:
                total_mins = 90
            tle = load_tle(mc.mtl_input_file)
            times, orbit, is_sunlight, minutes, _ = calculate_orbit_eclipse(
                tle,
                (self.gen.mtl_start_utc.year,
                 self.gen.mtl_start_utc.month,
                 self.gen.mtl_start_utc.day,
                 self.gen.mtl_start_utc.hour,
                 self.gen.mtl_start_utc.minute,
                 self.gen.mtl_start_utc.second),
                int(total_mins) + 1
            )
            saa_polygon, _ = circle_saa('df_for_contour.pkl', 200000)
            is_saa, _, _ = in_saa(times, saa_polygon, orbit)
            is_polar = [abs(orbit[i, 1]) > POLAR_LAT_THRESHOLD for i in range(len(orbit))]
            # minutes 是從 start_minute 開始的絕對分鐘數，轉為相對於 mtl_start_utc 的 offset
            minutes_rel = minutes - self.gen.mtl_start_utc.minute
        else:
            times = None

        self.gen.mtl_on_off_minutes_group = []
        self.gen.cmd_config_data_list = []

        for i in range(1, self.ui.verticalLayout.count()):
            item = self.ui.verticalLayout.itemAt(i).widget()
            layout = item.children()[0].layout()

            use_timing = layout.itemAt(1).widget().isChecked()   # use_timming
            row_start_dt = layout.itemAt(2).widget().dateTime().toPyDateTime()
            row_end_dt   = layout.itemAt(3).widget().dateTime().toPyDateTime()

            # checkbox 狀態（checked = 該區域也要開機）
            saa_on    = layout.itemAt(4).widget().isChecked()   # SAA_power_on
            polar_on  = layout.itemAt(5).widget().isChecked()   # polar_region_power_on
            sunlit_on = layout.itemAt(6).widget().isChecked()   # Sunlit_power_on

            if use_timing:
                # 直接用 row 的 start/end 時間，不做軌道過濾
                on_diff  = (row_start_dt - self.gen.mtl_start_utc).total_seconds() / 60
                off_diff = (row_end_dt   - self.gen.mtl_start_utc).total_seconds() / 60
                self.gen.mtl_on_off_minutes_group.append([on_diff, off_diff])
                self.gen.cmd_config_data_list.append(self._cmd_config_data.get(item, {}))
            elif has_tle:
                # 未勾選 use_timming：對整個計算範圍做軌道過濾，不限制 row 的時間範圍
                valid_idx = []
                for t_idx in range(len(minutes_rel)):
                    if not sunlit_on and is_sunlight[t_idx]:
                        continue
                    if not saa_on and is_saa[t_idx]:
                        continue
                    if not polar_on and is_polar[t_idx]:
                        continue
                    valid_idx.append(t_idx)

                if not valid_idx:
                    # 此 row 在條件下沒有可開機時段，跳過
                    continue

                # 把連續的 valid_idx 分組，每組取首尾作為 on/off
                groups = []
                group_start = valid_idx[0]
                prev = valid_idx[0]
                for idx in valid_idx[1:]:
                    if idx - prev > 1:
                        groups.append((group_start, prev))
                        group_start = idx
                    prev = idx
                groups.append((group_start, prev))

                for g_start, g_end in groups:
                    on_min  = float(minutes_rel[g_start])
                    off_min = float(minutes_rel[g_end])
                    self.gen.mtl_on_off_minutes_group.append([on_min, off_min])
                    self.gen.cmd_config_data_list.append(self._cmd_config_data.get(item, {}))
            else:
                # 沒有 TLE 檔案，無法計算軌道，跳過此 row
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(self, "缺少 TLE", "請先在主視窗載入 TLE 檔案後再 Generate。")
                return

        print(self.gen.mtl_on_off_minutes_group)
        self.gen.mtl_start_utc_2digit_year = datetime.strftime(self.gen.mtl_start_utc, '%y')

        # mtl_end_utc 從最後一個 off 時間推算
        if self.gen.mtl_on_off_minutes_group:
            last_off_min = self.gen.mtl_on_off_minutes_group[-1][-1]
            self.gen.mtl_end_utc = self.gen.mtl_start_utc + timedelta(minutes=last_off_min)
        else:
            self.gen.mtl_end_utc = self.gen.mtl_start_utc

        self.gen.mtl_write_xml()
        self.gen.cmd_write_on_xml()
