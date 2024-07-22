from pymmcore_plus import CMMCorePlus
from pymmcore_widgets import MDAWidget
from useq import MDASequence, MDAEvent
import numpy as np 
from collections import defaultdict
import json
from pathlib import Path
from time import perf_counter


class MetaDataWriter(): 
    def __init__(self, mmc: CMMCorePlus, tiff_save_path: str | Path) -> None:
        self.mmc = mmc
        self.frame_metadata = defaultdict(list)
        self._timestamps: list[float] = [] 
        self.tiff_save_path = Path(tiff_save_path)
        

        save_name= str(self.tiff_save_path.parts[-1]).split(".")[0] + "_meta.json"
        self.save_path = self.tiff_save_path / save_name

        self.mmc.mda.events.frameReady.connect(self.frameReady)
        self.mmc.mda.events.sequenceFinished.connect(self.sequenceFinished)

    def frameReady(
        self, frame: np.ndarray, event: MDAEvent
    ) -> None:
        """."""
        our_index = {}
        for dim in event.index.keys():
            our_index[dim] = event.index[dim]
        our_event = {"timestamp": perf_counter(), "min_start_time": event.min_start_time,
                      "index": our_index, "channel": event.channel.config, 
                      "exposure": event.exposure, "group": event.channel.group,
                      "x_pos": event.x_pos, "y_pos": event.y_pos}
        # get the position key to store the array in the group
        p_index = event.index.get("p", 0)
        key = f"p{p_index}"

        t = event.index.get("t", 0)
        self.frame_metadata[key].append(our_event or {})


    def sequenceFinished(self):
        # for position in self.frame_metadata.keys():
        #     for i, frame in enumerate(self.frame_metadata[position]):
        #         self.frame_metadata[position][i]['mda_event'] = json.loads(self.frame_metadata[position][i]['mda_event'].model_dump_json())

        with open(self.save_path, "w") as file:
            json.dump(dict(self.frame_metadata), file, indent=2)

        self.mmc.mda.events.frameReady.disconnect(self.frameReady)
        self.mmc.mda.events.sequenceFinished.disconnect(self.sequenceFinished)
