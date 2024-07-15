from qtpy.QtWidgets import (QApplication, QPushButton, QWidget, QGridLayout, QLabel)
from pymmcore_plus import CMMCorePlus
from pymmcore_widgets import (GroupPresetTableWidget, StageWidget, LiveButton, SnapButton,
                              ExposureWidget, ChannelGroupWidget, ShuttersWidget)

from zeiss_control.gui.preview import Preview
import os
from zeiss_control.gui._util.dark_theme import set_eda
from zeiss_control.gui._util.qt_classes import QMainWindowRestore, QWidgetRestore

os.environ['MICROMANAGER_PATH'] = "C:/Program Files/Micro-Manager-2.0.3/Micro-Manager_2.0.3_20240714"
class MainWindow(QMainWindowRestore):
    def __init__(self, mmcore:CMMCorePlus):
        super().__init__()
        self.main = QWidget()
        self.setWindowTitle("Micro-Manager")
        self.setCentralWidget(self.main)

        self.snap_button = SnapButton(mmcore=mmcore)
        self.live_button = LiveButton(mmcore=mmcore)
        self.exposure = ExposureWidget(mmcore=mmcore)
        self.channel_group = ChannelGroupWidget(mmcore=mmcore)

        self.main.setLayout(QGridLayout())
        self.main.layout().addWidget(self.live_button, 0, 0)
        self.main.layout().addWidget(self.snap_button, 1, 0)

        self.main.layout().addWidget(self.exposure, 0, 2)
        self.main.layout().addWidget(self.channel_group, 1, 2)

    def closeEvent(self, event):
        "Close all windows if main window is closed."
        app = QApplication.instance()
        app.closeAllWindows()
        super().closeEvent(event)
        
class Zeiss_StageWidget(QWidgetRestore):
    def __init__(self, mmc):
        super().__init__()
        stage1 = StageWidget("ZeissXYStage", mmcore=mmc)
        stage2 = StageWidget("ZeissFocusAxis", mmcore=mmc)
        self.setLayout(QGridLayout())
        self.layout().addWidget(stage1, 2, 0)
        self.layout().addWidget(stage2, 2, 1)
