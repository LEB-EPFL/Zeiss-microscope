from qtpy.QtWidgets import (QApplication, QPushButton, QWidget, QGridLayout, QLabel)
from pymmcore_plus import CMMCorePlus
from pymmcore_widgets import (GroupPresetTableWidget, StageWidget, LiveButton, SnapButton,
                              ExposureWidget, ChannelGroupWidget, ShuttersWidget)
from zeiss_control.gui.mda import ZeissMDAWidget
from zeiss_control.gui.preview import Preview
import os
from zeiss_control.gui._util.dark_theme import set_eda
from zeiss_control.gui._util.qt_classes import QMainWindowRestore, QWidgetRestore

os.environ['MICROMANAGER_PATH'] = "C:/Program Files/Micro-Manager-2.0"
class MainWindow(QMainWindowRestore):
    def __init__(self, mmcore:CMMCorePlus, eda:bool=False):
        super().__init__()
        self.main = QWidget()
        self.setWindowTitle("Micro-Manager")
        self.setCentralWidget(self.main)

        self.mda_window = ZeissMDAWidget(mmcore=mmcore)
        self.mda_window.setWindowTitle("MyMDA")

        self.snap_button = SnapButton(mmcore=mmcore)
        self.live_button = LiveButton(mmcore=mmcore)
        self.mda_button = QPushButton("MDA")

        self.exposure = ExposureWidget(mmcore=mmcore)
        self.channel_group = ChannelGroupWidget(mmcore=mmcore)

        self.main.setLayout(QGridLayout())
        self.main.layout().addWidget(self.live_button, 0, 0)
        self.main.layout().addWidget(self.snap_button, 1, 0)
        self.main.layout().addWidget(self.mda_button, 2, 0)

        self.main.layout().addWidget(self.exposure, 0, 2)
        self.main.layout().addWidget(self.channel_group, 1, 2)
        try:
            self.shutter_refl = ShuttersWidget('ZeissReflectedLightShutter', mmcore=mmcore)
            self.fluo_label = QLabel("Fluorescence")
            self.shutter_trans = ShuttersWidget('ZeissTransmittedLightShutter', mmcore=mmcore)
            self.brightfield_label = QLabel("Brightfield")
            self.main.layout().addWidget(self.shutter_refl, 2, 1)
            self.main.layout().addWidget(self.fluo_label, 3, 1)
            self.main.layout().addWidget(self.shutter_trans, 2, 2)
            self.main.layout().addWidget(self.brightfield_label, 3, 2)
        except:
            pass # Not on the Zeiss, omit this

        self.mda_button.pressed.connect(self._mda)

        if eda:
            self.eda_window = ZeissMDAWidget(mmcore=mmcore, include_run_button=False,
                                             save_filename="eda", saving=False)
            self.eda_window.setWindowTitle("MyEDA")
            set_eda(self.eda_window)
            self.eda_button = QPushButton("EDA")
            self.main.layout().addWidget(self.eda_button, 3, 0)
            self.eda_button.pressed.connect(self.eda_window.show)

    def _mda(self):
        self.mda_window.show()

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


if __name__ == "__main__":
    # from isim_control.settings import iSIMSettings

    from pymmcore_plus import CMMCorePlus
    from zeiss_control.gui._util.dark_theme import set_dark
    app = QApplication([])
    set_dark(app)

    mmc = CMMCorePlus.instance()
    mmc.loadSystemConfiguration("C:/Control/Zeiss-microscope/231031_ZeissAxioObserver7.cfg")

    stages = Zeiss_StageWidget(mmc)
    stages.show()

    from pymmcore_widgets import ImagePreview
    preview = Preview(mmcore=mmc)
    preview.show()

    #GUI
    frame = MainWindow(mmc)

    group_presets = GroupPresetTableWidget(mmcore=mmc)
    frame.main.layout().addWidget(group_presets, 5, 0, 1, 3)
    group_presets.show() # needed to keep events alive?
    frame.show()

    from zeiss_control.output import OutputGUI
    output = OutputGUI(mmc, frame.mda_window)
    app.exec_()

    if frame.eda:
        from eda_plugin.utility.core_event_bus import CoreEventBus
        event_bus = CoreEventBus()