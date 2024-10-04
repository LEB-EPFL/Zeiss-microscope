from pymmcore_plus.mda import MDAEngine
from pymmcore_plus import CMMCorePlus
from useq import MDAEvent

class SmartEngine(MDAEngine):
    def __init__(self, mmc: CMMCorePlus, use_hardware_sequencing: bool = True, galvos = None) -> None:
        super().__init__(mmc, use_hardware_sequencing)
        self.galvos = galvos

    def setup_single_event(self, event: MDAEvent) -> None:
        print("WE ARE SMART")
        # timepoints = [10, 11 , 12, 13, 14, 15, 30, 31 ,32, 33, 35]
        if event['config'] == "smart": #and event['index']['t'] in timepoints:
            self.galvos.setup()
        super().setup_single_event(event)