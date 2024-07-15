from qtpy.QtWidgets import QApplication, QDockWidget
from qtpy.QtCore import Qt
from zeiss_control.gui.main import Zeiss_StageWidget, MainWindow
from zeiss_control.gui.preview import Preview

from zeiss_control.gui._util.qt_classes import QWidgetRestore, QMainWindowRestore
from pymmcore_widgets import GroupPresetTableWidget
import sys


import logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
from pymmcore_plus import CMMCorePlus
from zeiss_control.gui._util.dark_theme import set_dark
app = QApplication([])
set_dark(app)


mmc = CMMCorePlus.instance()
try:
    mmc.loadSystemConfiguration("C:/Control/Zeiss-microscope/231031_ZeissAxioObserver7.cfg")
    mmc.setExposure(100)
    mmc.setChannelGroup("Channel")
    mmc.setConfig("Channel", "Brightfield")
    stages = Zeiss_StageWidget(mmc)
    stages.show()
except Exception as e:
    print(e)
    print("Couldn't load the Zeiss, going for Demo config")
    mmc.loadSystemConfiguration()


preview = Preview(mmcore=mmc)
preview.show()

#GUI
frame = MainWindow(mmc, eda=True)

group_presets = GroupPresetTableWidget(mmcore=mmc)
frame.main.layout().addWidget(group_presets, 5, 0, 1, 3)
group_presets.show() # needed to keep events alive?
frame.show()


from zeiss_control.gui.output import OutputGUI
output = OutputGUI(mmc, frame.mda_window)

frame.mda_window.send_new_settings()
app.exec_()
