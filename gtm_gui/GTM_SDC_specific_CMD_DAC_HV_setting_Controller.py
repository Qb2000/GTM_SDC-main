from PyQt5 import QtWidgets
from GTM_SDC_specific_CMD_DAC_HV_setting import Ui_Form


class CmdDacHvSettingWindow(QtWidgets.QWidget):
    """
    每個軌道 row 各自擁有一個獨立的 CmdDacHvSettingWindow 實例。
    config_data: dict，用來在視窗關閉後保留設定值，下次開啟時還原。
    """

    # 所有 QLineEdit 的 objectName 清單（依 Ui_Form 定義）
    FIELD_NAMES = (
        [f"M_B_ch{i}" for i in range(32)] + ["M_B_HV_DAC_setting"] +
        [f"M_A_ch{i}" for i in range(32)] + ["M_A_HV_DAC_setting"] +
        [f"S_B_ch{i}" for i in range(32)] + ["S_B_HV_DAC_setting"] +
        [f"S_A_ch{i}" for i in range(32)] + ["S_A_HV_DAC_setting"]
    )

    def __init__(self, config_data: dict, row_index: int, parent=None):
        super().__init__(parent)
        self.config_data = config_data  # 共用 dict，與 MTL row 共享參考
        self.row_index = row_index

        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.setWindowTitle(f"CMD DAC/HV Setting - Orbit {row_index}")

        self._load_from_config()
        self.ui.Save_CMD.clicked.connect(self._save_and_close)

    # ------------------------------------------------------------------
    def _load_from_config(self):
        """把 config_data 的值填回 UI 欄位。"""
        for name in self.FIELD_NAMES:
            widget = self.findChild(QtWidgets.QLineEdit, name)
            if widget and name in self.config_data:
                widget.setText(self.config_data[name])

    def _save_and_close(self):
        """把 UI 欄位值存入 config_data，然後關閉視窗。"""
        for name in self.FIELD_NAMES:
            widget = self.findChild(QtWidgets.QLineEdit, name)
            if widget:
                self.config_data[name] = widget.text()
        self.close()

    def closeEvent(self, event):
        """視窗直接關閉（X 按鈕）時也自動儲存。"""
        self._save_and_close()
        super().closeEvent(event)
