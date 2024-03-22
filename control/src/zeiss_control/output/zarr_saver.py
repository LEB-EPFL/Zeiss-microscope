from zeiss_control.output._util.zarr_saver import OMEZarrWriter

from useq import MDAEvent, MDASequence
import numpy as np

from pathlib import Path
from pymmcore_plus import CMMCorePlus
from eda_plugin.utility.core_event_bus import CoreEventBus
import time


class CoreOMEZarrWriter(OMEZarrWriter):

    def __init__(self, folder: Path | str, mmcore: CMMCorePlus, event_bus:CoreEventBus):
        super().__init__(folder, overwrite=True)
        self.event_bus = event_bus
        self._mmc = mmcore
        self.last_sequence = None
        self._mm_config = self._mmc.getSystemState().dict()
        self._mmc.mda.events.sequenceStarted.connect(self.sequenceStarted)
        self._mmc.mda.events.frameReady.connect(self.frameReady)
        self._mmc.mda.events.sequenceFinished.connect(self.sequenceFinished)
        self.event_bus.new_network_image.connect(self.net_frameReady)

    def sequenceStarted(self, seq: MDASequence) -> None:
        self.last_sequence = seq
        self.start_time = time.perf_counter()
        return super().sequenceStarted(seq)

    def net_frameReady(self, img: np.ndarray, timepoint: tuple):
        print("________________ FRAMEREADY received in CoreOMeZarrWriter ___________________")
        event = MDAEvent(channel={"config": "Network"},
                          index={'t': timepoint[0],
                                 'c': self.current_sequence.sizes.get("c", 1)-1})
        self.frameReady(img, event)

    def frameReady(self, frame: np.ndarray, event: MDAEvent) -> None:
        print("SAVING FRAME", event)
        timestamp = time.perf_counter() - self.start_time
        return super().frameReady(frame, event, {"ReceivedTime": timestamp})