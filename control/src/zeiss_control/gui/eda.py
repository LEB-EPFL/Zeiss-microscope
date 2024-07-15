from qtpy.QtWidgets import QApplication, QDockWidget
from qtpy.QtCore import Qt
from zeiss_control.gui.main import Zeiss_StageWidget, MainWindow
from zeiss_control.gui.preview import Preview

from zeiss_control.gui._util.qt_classes import QWidgetRestore, QMainWindowRestore
from pymmcore_widgets import GroupPresetTableWidget
import sys


class EDAMainGUI(QMainWindowRestore):
    def __init__(self):
        """Set up GUI and establish communication with the EventBus."""
        super().__init__()
        self.setWindowTitle("Event Driven Acquisition")

        self.dock_widgets = []
        self.widgets = []

    def add_dock_widget(self, widget: QWidgetRestore, name = None, area: int = 1):
        dock_widget = QDockWidget(name, self)
        dock_widget.setWidget(widget)
        self.dock_widgets.append(dock_widget)
        self.widgets.append(widget)
        self.addDockWidget(Qt.DockWidgetArea(area), dock_widget)\

    def closeEvent(self, e):
        for widget in self.widgets:
            widget.closeEvent(e)


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



if frame.eda_window:
    keras = True #"sim_net_img"
    manual = False
    print("Spinning up EDA")
    from eda_plugin.utility.core_event_bus import CoreEventBus
    if keras is True:
        from eda_plugin.analysers.keras import KerasAnalyser as Analyser
    elif keras == "sim_net_img":
        from eda_plugin.analysers.keras import NetworkImageTester as Analyser
    else:
        from eda_plugin.analysers.image import ImageAnalyser as Analyser
    if manual:
        from eda_plugin.interpreters.manual import ManualInterpreter as Interpreter
    else:
        from eda_plugin.interpreters.presets import PresetsInterpreter as Interpreter
    from eda_plugin.actuators.pymmc_engine import CoreRunner as CoreRunner


    event_bus = CoreEventBus(mmc, frame.mda_window, frame.eda_window, preview)

    actuator = CoreRunner(mmc, event_bus)
    analyser = Analyser(event_bus)
    interpreter = Interpreter(event_bus)

    gui = EDAMainGUI()
    gui.add_dock_widget(analyser.gui, "Analyser")
    gui.add_dock_widget(interpreter.gui, "Interpreter")
    gui.add_dock_widget(actuator.gui, "Actuator")
    gui.show()

    from zeiss_control.gui.event_score import EventScorePlot
    score = EventScorePlot(event_bus)
    score.show()

    from zeiss_control.gui._util.dark_theme import set_eda
    for widget in [analyser.gui, interpreter.gui, actuator.gui, gui, score]:
        set_eda(widget)


from zeiss_control.gui.output import OutputGUI
output = OutputGUI(mmc, frame.mda_window, event_bus)

frame.mda_window.send_new_settings()
if frame.eda_window:
    frame.eda_window.send_new_settings()
app.exec_()
