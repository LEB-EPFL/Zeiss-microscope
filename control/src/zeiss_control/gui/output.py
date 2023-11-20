from pymmcore_plus import CMMCorePlus
from zeiss_control.output.datastore import QLocalDataStore
from zeiss_control.output.stack_viewer import StackViewer
from useq import MDASequence
from zeiss_control.output.saver import CoreOMETiffWriter
from qtpy.QtCore import QObject


class OutputGUI(QObject):
    def __init__(self, mmcore: CMMCorePlus, mda_gui=None):
        super().__init__()
        self.mmc = mmcore
        self.mmc.mda.events.sequenceStarted.connect(self.make_viewer)
        self.mda_gui = mda_gui
        if self.mda_gui:
            self.mda_gui.new_save_settings.connect(self.new_save_settings)
        mda_gui.new_save_settings_set()

    def new_save_settings(self, save: bool, path: str):
        self.path = path
        self.save = save
        print("New settings", save, path)

    def make_viewer(self, sequence:MDASequence):
        sizes = sequence.sizes
        shape = [sizes.get('t', 1),
                    sizes.get('z', 1),
                    sizes.get('c', 1),
                    self.mmc.getImageHeight(),
                    self.mmc.getImageWidth()]
        self.datastore = QLocalDataStore(shape, mmcore=self.mmc)
        if self.save:
            self.writer = CoreOMETiffWriter(self.path, self.mmc)
            self.writer.sequenceStarted(sequence)
            self.mmc.mda.events.frameReady.connect(self.writer.frameReady)
        self.viewer = StackViewer(datastore=self.datastore, mmcore=self.mmc,
                                  sequence=sequence)
        self.viewer.show()