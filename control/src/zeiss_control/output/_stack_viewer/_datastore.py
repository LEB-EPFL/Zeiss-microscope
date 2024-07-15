from __future__ import annotations

from typing import TYPE_CHECKING

from psygnal import Signal
from zeiss_control.output._util.zarr_saver import POS_PREFIX, OMEZarrWriter
from useq import MDAEvent
import yaml
from pathlib import Path
import time

if TYPE_CHECKING:
    from typing import Any

    import numpy as np
    import useq


class QOMEZarrDatastore(OMEZarrWriter):
    frame_ready = Signal(MDAEvent)

    def __init__(self, store = None) -> None:
        self.store = store
        super().__init__(store=store)

    def sequenceStarted(self, sequence: useq.MDASequence) -> None:
        self._used_axes = tuple(x for x in sequence.used_axes if x not in ['p'])
        self.start_time = time.perf_counter()
        super().sequenceStarted(sequence)
        if self.store:
            if self._mm_config:
                with open(Path(self.store)/'mm_config.txt', 'w') as outfile:
                    yaml.dump(self._mm_config, outfile, default_flow_style=False)

    def frameReady(
        self,
        frame: np.ndarray,
        event: useq.MDAEvent,
        meta: dict[Any, Any] = None,
    ) -> None:
        timestamp = time.perf_counter() - self.start_time
        meta = {"DeltaT": timestamp, **(meta or {})}
        super().frameReady(frame, event, meta or {})
        self.frame_ready.emit(event)

    def get_frame(self, event: MDAEvent) -> np.ndarray:
        key = f'{POS_PREFIX}{event.index.get("p", 0)}'
        ary = self.position_arrays[key]

        index = tuple(event.index.get(k) for k in self._used_axes)
        data: np.ndarray = ary[index]
        return data
