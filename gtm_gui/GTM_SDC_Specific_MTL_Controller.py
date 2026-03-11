from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
from GTM_SDC_specific_MLT import Ui_specific_MTL_window  
from datetime import datetime, timedelta



class SpecificMTLWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_specific_MTL_window()
        self.ui.setupUi(self)
        self.row_count = 0  # 因為 rowTemplateWidget 已經是第一個
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

        # 複製每個 widget（依照你的順序）
        grid_layout.addWidget(clone_label(self.ui.label), 0, 0)
        grid_layout.addWidget(clone_datetimeedit(self.ui.dateTimeEdit), 0, 1)
        grid_layout.addWidget(clone_datetimeedit(self.ui.dateTimeEdit_2), 0, 2)
        grid_layout.addWidget(clone_checkbox(self.ui.SAA_power_on), 0, 3)
        grid_layout.addWidget(clone_checkbox(self.ui.polar_region_power_on), 0, 4)
        grid_layout.addWidget(clone_checkbox(self.ui.Sunlit_power_on), 0, 5)

        # 加、減按鈕
        add_btn = clone_button(self.ui.add_row, "+")
        remove_btn = clone_button(self.ui.remove_row, "-")
        grid_layout.addWidget(add_btn, 0, 6)
        grid_layout.addWidget(remove_btn, 0, 7)

        # 按鈕連接功能（可動態控制）
        add_btn.clicked.connect(self.add_row_function)
        remove_btn.clicked.connect(lambda: self.remove_specific_row(new_row))
        
        
        # 插入指定位置
        if self.row_count > 0:
            for i in range(self.ui.verticalLayout.count()):
                item = self.ui.verticalLayout.itemAt(i).widget()
                # print(i)
                # print(sender)
                # print(item)
                # print(item.children()[0])
                # print(item.children()[0].layout())

                if item.children()[0].layout().itemAt(6).widget() == sender:
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

    def remove_specific_row(self, row_widget):
        # 從 layout 中移除 row，然後刪除
        self.ui.verticalLayout.removeWidget(row_widget)
        row_widget.deleteLater()
        self.row_count -= 1
        self.update_row_numbers()
        if self.row_count == 1:
           row_widget = self.ui.verticalLayout.itemAt(1).widget()
           remove_botton = row_widget.children()[0].layout().itemAt(7).widget()
           remove_botton.setEnabled(False)
  
    def update_row_numbers(self):
        for i in range(1,self.ui.verticalLayout.count()):
            row_widget = self.ui.verticalLayout.itemAt(i).widget()
            if row_widget:
                number_label = row_widget.children()[0].layout().itemAt(0).widget()
                number_label.setText(f"{i}.")
                remove_botton = row_widget.children()[0].layout().itemAt(7).widget()
                if self.row_count > 1:
                    remove_botton.setEnabled(True)             
                 

    def generate(self): #default generate
        from GTM_SDC_UI_Controller_Mtl_Cmd import UiMtlCmd
        self.gen = UiMtlCmd()
        item = self.ui.verticalLayout.itemAt(1).widget()   
        start_dt_widget = item.children()[0].layout().itemAt(1).widget()
        self.gen.mtl_start_utc = start_dt_widget.dateTime().toPyDateTime()
        
        item = self.ui.verticalLayout.itemAt(self.ui.verticalLayout.count()-1).widget()
        end_dt_widget = item.children()[0].layout().itemAt(2).widget()
        self.gen.mtl_end_utc = end_dt_widget.dateTime().toPyDateTime()
        print(self.gen.mtl_end_utc)
        
        
        self.gen.mtl_on_off_minutes_group = []
        
        for i in range(1,self.ui.verticalLayout.count()):
            item = self.ui.verticalLayout.itemAt(i).widget()
            
            start_dt_widget = item.children()[0].layout().itemAt(1).widget().dateTime().toPyDateTime()
            end_dt_widget = item.children()[0].layout().itemAt(2).widget().dateTime().toPyDateTime()

            self.ui.on_diff = start_dt_widget - self.gen.mtl_start_utc
            self.ui.off_diff = end_dt_widget - self.gen.mtl_start_utc
            self.gen.mtl_on_off_minutes_group.append([(self.ui.on_diff.total_seconds() / 60),(self.ui.off_diff.total_seconds() / 60)])
            
        print(self.gen.mtl_on_off_minutes_group)   
        # self.mtl_start_utc.year = 2025
        # self.mtl_start_utc.month = 6
        # self.mtl_start_utc.day = 23
        # self.mtl_start_utc.hour = 0
        # self.mtl_start_utc.minute =  0
        # self.mtl_start_utc.second = 1
        self.gen.mtl_start_utc_2digit_year = datetime.strftime(self.gen.mtl_start_utc, '%y')
        # self.gen.mtl_end_utc = self.gen.mtl_start_utc + timedelta(minutes=30)
        # self.gen.mtl_on_off_minutes_group = [[0,30]]
        self.gen.mtl_write_xml()

        self.gen.cmd_write_on_xml()
        self.gen.cmd_write_off_xml()