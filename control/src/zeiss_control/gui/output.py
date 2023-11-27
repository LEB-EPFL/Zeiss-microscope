from pymmcore_plus import CMMCorePlus
from zeiss_control.output.datastore import QLocalDataStore
from zeiss_control.output.stack_viewer import StackViewer
from useq import MDASequence, Channel
from zeiss_control.output.saver import CoreOMETiffWriter
from qtpy.QtCore import QObject

from eda_plugin.utility.core_event_bus import CoreEventBus

class OutputGUI(QObject):
    def __init__(self, mmcore: CMMCorePlus, mda_gui=None, eda_event_bus:CoreEventBus=None):
        super().__init__()
        self.mmc = mmcore
        self.mmc.mda.events.sequenceStarted.connect(self.make_viewer)
        self.mda_gui = mda_gui
        if self.mda_gui:
            self.mda_gui.new_save_settings.connect(self.new_save_settings)
            mda_gui.new_save_settings_set()

        self.eda_event_bus = eda_event_bus

    def new_save_settings(self, save: bool, path: str):
        self.path = path
        self.save = save
        print("New settings", save, path)

    def make_viewer(self, sequence:MDASequence):
        shape, sequence = self.adjust_sequence(sequence)
        self.datastore = QLocalDataStore(shape, mmcore=self.mmc,
                                          eda_event_bus=self.eda_event_bus)
        if self.save:
            self.writer = CoreOMETiffWriter(self.path, self.mmc, self.datastore)
            self.writer.sequenceStarted(sequence)
        self.viewer = StackViewer(datastore=self.datastore, mmcore=self.mmc,
                                  sequence=sequence)
        self.viewer.show()

    def adjust_sequence(self, sequence: MDASequence):
        if sequence.metadata.get("EDA", False):
            channels = list(sequence.channels) + [Channel(config="Network")]
            sequence = MDASequence(
                channels=channels,
                axis_order=sequence.axis_order,
                grid_plan=sequence.grid_plan,
                time_plan=sequence.time_plan,
                z_plan=sequence.z_plan,
                autofocus_plan=sequence.autofocus_plan,
            )
        sizes = sequence.sizes
        shape = [sizes.get('t', 1),
                    sizes.get('z', 1),
                    sizes.get('c', 1),
                    self.mmc.getImageHeight(),
                    self.mmc.getImageWidth()]
        return shape, sequence