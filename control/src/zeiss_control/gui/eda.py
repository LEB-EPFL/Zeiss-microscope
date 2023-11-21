from qtpy.QtWidgets import QApplication
from zeiss_control.gui.main import Zeiss_StageWidget, MainWindow
from pymmcore_widgets import GroupPresetTableWidget
import sys 


# from isim_control.settings import iSIMSettings
import logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
from pymmcore_plus import CMMCorePlus
from zeiss_control.gui.dark_theme import set_dark
app = QApplication([])
set_dark(app)

mmc = CMMCorePlus.instance()
mmc.loadSystemConfiguration("C:/Control/Zeiss-microscope/231031_ZeissAxioObserver7.cfg")

# stages = Zeiss_StageWidget(mmc)
# stages.show()

from pymmcore_widgets import ImagePreview
preview = ImagePreview(mmcore=mmc)
preview.show()

#GUI
frame = MainWindow(mmc, eda=True)

group_presets = GroupPresetTableWidget(mmcore=mmc)
frame.main.layout().addWidget(group_presets, 5, 0, 1, 3)
group_presets.show() # needed to keep events alive?
frame.show()

from zeiss_control.gui.output import OutputGUI
output = OutputGUI(mmc, frame.mda_window)


if frame.eda_window:
    keras = False
    print("Spinning up EDA")
    from eda_plugin.utility.core_event_bus import CoreEventBus
    if keras:
        from eda_plugin.analysers.keras import KerasAnalyser as Analyser
    else:
        from eda_plugin.analysers.image import ImageAnalyser as Analyser
    from eda_plugin.interpreters.presets import PresetsInterpreter
    from eda_plugin.actuators.pymmc_engine import CoreRunner


    event_bus = CoreEventBus(mmc, frame.mda_window, frame.eda_window)

    actuator = CoreRunner(mmc, event_bus)
    analyser = Analyser(event_bus)
    interpreter = PresetsInterpreter(event_bus)

    analyser.gui.show()
    interpreter.gui.show()
    actuator.gui.show()

    frame.mda_window.send_new_settings()

app.exec_()
