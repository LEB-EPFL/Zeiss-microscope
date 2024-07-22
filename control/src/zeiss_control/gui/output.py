from pymmcore_plus import CMMCorePlus
from zeiss_control.output.datastore import QLocalDataStore
from zeiss_control.output.stack_viewer import StackViewer
from zeiss_control.output._stack_viewer import QOMEZarrDatastore
from zeiss_control.output._stack_viewer import StackViewer as ZarrStackViewer
from zeiss_control.output.tiff_saver import CoreOMETiffWriter
from zeiss_control.backend.meta import MetaDataWriter
import time
from useq import MDASequence, Channel, MDAEvent
# from zeiss_control.output.zarr_saver import CoreOMEZarrWriter
from qtpy.QtCore import QObject, Signal
import numpy as np
from eda_plugin.utility.core_event_bus import CoreEventBus

class OutputGUI(QObject):
    net_frameReady = Signal(np.ndarray, MDAEvent)
    def __init__(self, mmcore: CMMCorePlus, mda_gui=None, eda_event_bus:CoreEventBus=None):
        super().__init__()
        self.mmc = mmcore
        self.mmc.mda.events.sequenceStarted.connect(self.make_viewer)
        self.mmc.mda.events.sequenceFinished.connect(self.sequence_finished)
        self.mda_gui = mda_gui
        if self.mda_gui:
            self.mda_gui.new_save_settings.connect(self.new_save_settings)
            mda_gui.new_save_settings_set()

        self.eda_event_bus = eda_event_bus
        self.ready = False
        self.writer = None

    def new_save_settings(self, save: bool, path: str):
        self.path = path
        self.save = save
        print("New settings", save, path)

    def make_viewer(self, sequence:MDASequence):
        shape, sequence = self.adjust_sequence(sequence)
        self.n_channels = sequence.sizes.get('c', 1)
        if self.path[-4:] == "zarr":
            if self.save:
                path = self.path
            else:
                path = None

            self.datastore = QOMEZarrDatastore(path)
            self.datastore._mm_config = self.mmc.getSystemState().dict()
            self.mmc.mda.events.frameReady.connect(self.datastore.frameReady)
            self.net_frameReady.connect(self.datastore.frameReady)
            self.mmc.mda.events.sequenceStarted.connect(self.datastore.sequenceStarted)
            self.eda_event_bus.new_network_image.connect(self.net_frame_ready)
            self.viewer = ZarrStackViewer(datastore=self.datastore, mmcore=self.mmc,
                                    sequence=sequence, transform=(90, False, True))
            self.datastore.sequenceStarted(sequence)
        else:
            self.datastore = QLocalDataStore(shape, mmcore=self.mmc,
                                              eda_event_bus=self.eda_event_bus)
            if self.save:
                self.writer = CoreOMETiffWriter(self.path, self.mmc, self.eda_event_bus)
                self.metadatawriter = MetaDataWriter(self.mmc, self.path)
                self.writer.sequenceStarted(sequence)
            self.viewer = StackViewer(datastore=self.datastore, mmcore=self.mmc,
                                    sequence=sequence)
        self.ready = True
        self.viewer.show()

    def net_frame_ready(self, img, timepoint):
        print("--------------------NETWORK FRAME READY-------------------")
        event = MDAEvent(channel={"config": "Network"}, index={'t': timepoint[0], 'c': self.n_channels-1})
        if self.ready:
            self.net_frameReady.emit(img, event)

    def sequence_finished(self, sequence: MDASequence):
        if self.writer:
            time.sleep(1)
            self.writer = None
        elif self.datastore:
            time.sleep(1)
            self.datastore.sequenceFinished(sequence)
            self.disconnect_datastore()
            self.datastore = None
        self.ready = False

    def disconnect_datastore(self):
        if isinstance(self.datastore, QOMEZarrDatastore):
            self.mmc.mda.events.frameReady.disconnect(self.datastore.frameReady)
            self.net_frameReady.disconnect(self.datastore.frameReady)
            self.mmc.mda.events.sequenceStarted.disconnect(self.datastore.sequenceStarted)
            self.eda_event_bus.new_network_image.disconnect(self.net_frame_ready)

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
                    sizes.get('g', 1),
                    self.mmc.getImageHeight(),
                    self.mmc.getImageWidth()]
        return shape, sequence