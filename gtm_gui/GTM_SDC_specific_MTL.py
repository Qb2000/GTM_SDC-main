# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'GTM_SDC_specific_MTL.ui'
#
# Created by: PyQt5 UI code generator 5.12.3
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_specific_MTL_window(object):
    def setupUi(self, specific_MTL_window):
        specific_MTL_window.setObjectName("specific_MTL_window")
        specific_MTL_window.resize(514, 640)
        self.centralwidget = QtWidgets.QWidget(specific_MTL_window)
        self.centralwidget.setObjectName("centralwidget")
        self.Generate_specific_MTL = QtWidgets.QPushButton(self.centralwidget)
        self.Generate_specific_MTL.setGeometry(QtCore.QRect(130, 530, 241, 41))
        self.Generate_specific_MTL.setObjectName("Generate_specific_MTL")
        self.groupBox = QtWidgets.QGroupBox(self.centralwidget)
        self.groupBox.setGeometry(QtCore.QRect(10, 10, 491, 471))
        self.groupBox.setFlat(False)
        self.groupBox.setCheckable(False)
        self.groupBox.setObjectName("groupBox")
        self.gridLayoutWidget = QtWidgets.QWidget(self.groupBox)
        self.gridLayoutWidget.setGeometry(QtCore.QRect(10, 20, 472, 53))
        self.gridLayoutWidget.setObjectName("gridLayoutWidget")
        self.gridLayout = QtWidgets.QGridLayout(self.gridLayoutWidget)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setObjectName("gridLayout")
        self.add_row = QtWidgets.QPushButton(self.gridLayoutWidget)
        self.add_row.setEnabled(True)
        self.add_row.setObjectName("add_row")
        self.gridLayout.addWidget(self.add_row, 0, 2, 1, 1)
        self.remove_row = QtWidgets.QPushButton(self.gridLayoutWidget)
        self.remove_row.setObjectName("remove_row")
        self.gridLayout.addWidget(self.remove_row, 0, 3, 1, 1)
        self.polar_region_power_on = QtWidgets.QCheckBox(self.gridLayoutWidget)
        self.polar_region_power_on.setObjectName("polar_region_power_on")
        self.gridLayout.addWidget(self.polar_region_power_on, 0, 1, 1, 1)
        self.SAA_power_on = QtWidgets.QCheckBox(self.gridLayoutWidget)
        self.SAA_power_on.setObjectName("SAA_power_on")
        self.gridLayout.addWidget(self.SAA_power_on, 0, 0, 1, 1)
        specific_MTL_window.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(specific_MTL_window)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 514, 21))
        self.menubar.setObjectName("menubar")
        specific_MTL_window.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(specific_MTL_window)
        self.statusbar.setObjectName("statusbar")
        specific_MTL_window.setStatusBar(self.statusbar)

        self.retranslateUi(specific_MTL_window)
        QtCore.QMetaObject.connectSlotsByName(specific_MTL_window)

    def retranslateUi(self, specific_MTL_window):
        _translate = QtCore.QCoreApplication.translate
        specific_MTL_window.setWindowTitle(_translate("specific_MTL_window", "MainWindow"))
        self.Generate_specific_MTL.setText(_translate("specific_MTL_window", "Generate"))
        self.groupBox.setTitle(_translate("specific_MTL_window", "MTL "))
        self.add_row.setText(_translate("specific_MTL_window", "+"))
        self.remove_row.setText(_translate("specific_MTL_window", "-"))
        self.polar_region_power_on.setText(_translate("specific_MTL_window", "polar_region"))
        self.SAA_power_on.setText(_translate("specific_MTL_window", "SAA"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    specific_MTL_window = QtWidgets.QMainWindow()
    ui = Ui_specific_MTL_window()
    ui.setupUi(specific_MTL_window)
    specific_MTL_window.show()
    sys.exit(app.exec_())
