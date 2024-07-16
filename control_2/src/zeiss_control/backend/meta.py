from pymmcore_plus import CMMCorePlus
from pymmcore_plus.metadata import FrameMetaV1
from pymmcore_widgets import MDAWidget
from useq import MDASequence, MDAEvent
import numpy as np 
from collections import defaultdict
import json



class MetaDataWriter(): 
    def __init__(self, mda_widget: MDAWidget, mmc: CMMCorePlus) -> None:
        self.mda_widget = mda_widget
        self.mmc = mmc
        self.frame_metadata: defaultdict[str, list[FrameMetaV1]] = defaultdict(list)
        self._timestamps: list[float] = []
        self.save_path: None

        self.mmc.mda.events.sequenceStarted.connect(self.sequenceStarted)
    
    def sequenceStarted(self, sequence: MDASequence):
        if "ome-tiff" not in self.mda_widget.save_info._writer_combo.currentText():
            return  
        if not self.mda_widget.save_info.isChecked():
            return
        self.frame_metadata.clear()
        
        save_dir = self.mda_widget.save_info.save_dir.text() 
        save_name = self.mda_widget.save_info.save_name.text().split(".")[0] + "_meta.json"
        self.save_path = save_dir + "/" + save_name

        self.mmc.mda.events.frameReady.connect(self.frameReady)
        self.mmc.mda.events.sequenceFinished.connect(self.sequenceFinished)

    def frameReady(
        self, frame: np.ndarray, event: MDAEvent, meta: FrameMetaV1
    ) -> None:
        """."""
        # get the position key to store the array in the group
        p_index = event.index.get("p", 0)
        key = f"p{p_index}"

        t = event.index.get("t", 0)
        if t >= len(self._timestamps) and "runner_time_ms" in meta:
            self._timestamps.append(meta["runner_time_ms"])
        self.frame_metadata[key].append(meta or {})


    def sequenceFinished(self):
        for position in self.frame_metadata.keys():
            for i, frame in enumerate(self.frame_metadata[position]):
                self.frame_metadata[position][i]['mda_event'] = json.loads(self.frame_metadata[position][i]['mda_event'].model_dump_json())

        with open(self.save_path, "w") as file:
            json.dump(self.frame_metadata, file, indent=2)

        self.mmc.mda.events.frameReady.disconnect(self.frameReady)
        self.mmc.mda.events.sequenceFinished.disconnect(self.sequenceFinished)
