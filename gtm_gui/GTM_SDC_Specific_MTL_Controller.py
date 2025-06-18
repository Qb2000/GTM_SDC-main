
from PyQt5 import QtCore, QtGui, QtWidgets
from GTM_SDC_specific_MTL import Ui_specific_MTL_window  

class SpecificMTLWindow(QtWidgets.QMainWindow):
    def __init__(self):
    #     super().__init__()
    #     self.ui = Ui_specific_MTL_window()
    #     self.ui.setupUi(self)
    #     self.setup_controller()
    #     self.current_row = 0

    # def setup_controller(self):

    #     self.ui.Generate_specific_MTL.setEnabled(False)
    #     self.ui.remove_row.setEnabled(False)
        
    #     self.ui.add_row.clicked.connect(self.add_row_function)
        
        super().__init__()  

        self.setWindowTitle("Specific MTL")
        self.resize(400, 600)

        # 中央元件
        central_widget = QtWidgets.QWidget(self)
        self.setCentralWidget(central_widget)

        # 整體垂直 layout
        main_layout = QtWidgets.QVBoxLayout(central_widget)

        # 加一個 groupbox 裡面放 row 區域
        self.groupBox = QtWidgets.QGroupBox("orbit", self)
        self.rows_layout = QtWidgets.QVBoxLayout(self.groupBox)
        main_layout.addWidget(self.groupBox)

        # 最下方 + 按鈕
        self.add_row_btn = QtWidgets.QPushButton("＋ add new orbit")
        main_layout.addWidget(self.add_row_btn)
        self.add_row_btn.clicked.connect(self.add_row_function)
        self.generate_btn = QtWidgets.QPushButton("Generate MTL")
        main_layout.addWidget(self.generate_btn)
        self.generate_btn.clicked.connect(self.generate_specific_mtl)

        # 初始一列
        self.add_row_function()

    def add_row_function(self, after_widget=None):
        row_widget = QtWidgets.QWidget()
        row_layout = QtWidgets.QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)

        # 編號 label（稍後會更新）
        number_label = QtWidgets.QLabel("")

        cb1 = QtWidgets.QCheckBox("SAA")
        cb2 = QtWidgets.QCheckBox("Polar Region")
        cb3 = QtWidgets.QCheckBox("Sunlit")
        add_btn = QtWidgets.QPushButton("+")
        remove_btn = QtWidgets.QPushButton("-")

        row_layout.addWidget(number_label)
        row_layout.addWidget(cb1)
        row_layout.addWidget(cb2)
        row_layout.addWidget(cb3)
        row_layout.addWidget(add_btn)
        row_layout.addWidget(remove_btn)

        # 插入指定位置
        if after_widget:
            index = self.rows_layout.indexOf(after_widget)
            self.rows_layout.insertWidget(index + 1, row_widget)
        else:
            self.rows_layout.addWidget(row_widget)

        # 事件綁定
        add_btn.clicked.connect(lambda: self.add_row_function(row_widget))
        remove_btn.clicked.connect(lambda: self.remove_row(row_widget))

        # 更新所有 row 編號
        
        self.update_row_numbers()

    def remove_row(self, row_widget):
        self.rows_layout.removeWidget(row_widget)
        row_widget.setParent(None)
        row_widget.deleteLater()
        self.update_row_numbers()

    def update_row_numbers(self):
        for i in range(self.rows_layout.count()):
            row_widget = self.rows_layout.itemAt(i).widget()
            if row_widget:
                row_layout = row_widget.layout()
                number_label = row_layout.itemAt(0).widget()  # 第一個是 QLabel
                number_label.setText(f"{i + 1}.")
    def generate_specific_mtl(self):
        print(1)
