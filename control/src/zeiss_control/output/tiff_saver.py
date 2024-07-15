"""OME.TIFF writer for MDASequences.
Borrowed from https://github.com/pymmcore-plus/pymmcore-plus/pull/265
Should be replaced once this is merged.
"""

from __future__ import annotations
from pymmcore_plus import CMMCorePlus

# from zeiss_control.output.datastore import QLocalDataStore
from eda_plugin.utility.core_event_bus import CoreEventBus
from datetime import timedelta
from typing import TYPE_CHECKING, Any, cast
from pathlib import Path
import yaml
from useq import MDAEvent


if TYPE_CHECKING:

    import numpy as np
    import useq


class CoreOMETiffWriter:
    def __init__(self, folder: Path | str, mmcore: CMMCorePlus, event_bus:CoreEventBus) -> None:
        try:
            import tifffile  # noqa: F401
            import yaml
        except ImportError as e:  # pragma: no cover
            raise ImportError(
                "tifffile and yaml is required to use this handler. "
                "Please `pip install tifffile`. and pyyaml"
            ) from e

        # create an empty OME-TIFF file
        self._folder = Path(folder)
        self.event_bus = event_bus

        self._mmaps: None | np.memmap = None
        self._current_sequence: None | useq.MDASequence = None
        self.n_grid_positions: int = 1

        self._mmc = mmcore
        self._mm_config = self._mmc.getSystemState().dict()
        self._mmc.mda.events.sequenceStarted.connect(self.sequenceStarted)
        self._mmc.mda.events.frameReady.connect(self.frameReady)
        self.event_bus.new_network_image.connect(self.net_frameReady)

    def sequenceStarted(self, seq: useq.MDASequence) -> None:
        self._set_sequence(seq)

    def net_frameReady(self, img: np.ndarray, timepoint: tuple):
        event = MDAEvent(channel={"config": "Network"},
                          index={'t': timepoint[0],
                                 'c': self._current_sequence.sizes.get("c", 1)-1})
        self.frameReady(img, event)

    def frameReady(self, frame: np.ndarray, event: useq.MDAEvent) -> None:
        # no meta input for this version yet.
        if event is None:
            return
        if self._mmaps is None:
            if not self._current_sequence:
                # just in case sequenceStarted wasn't called
                self._set_sequence(event.sequence)  # pragma: no cover

            if not (seq := self._current_sequence):
                raise NotImplementedError(
                    "Writing zarr without a MDASequence not yet implemented"
                )

            mmap = self._create_seq_memmap(frame, seq)[event.index.get("g", 0)]
        else:
            print("INDEX---------------\n", event.index)
            print("n_mmpas:", len(self._mmaps))
            mmap = self._mmaps[event.index.get("g", 0)]

        # WRITE DATA TO DISK
        index = tuple(event.index.get(k) for k in self._used_axes)
        print("\033[1mWRITING image from", event.channel.config, "\033[0m")
        print(frame.max())
        mmap[index] = frame
        mmap.flush()

    # -------------------- private --------------------

    def _set_sequence(self, seq: useq.MDASequence | None) -> None:
        """Set the current sequence, and update the used axes."""
        self._folder.mkdir(parents=True, exist_ok=True)
        self._current_sequence = seq
        if seq:
            self._used_axes = tuple(seq.used_axes)
            self.n_grid_positions = max([seq.sizes.get('g', 1), 1])
            if 'g' in seq.used_axes:
                self._used_axes = tuple(a for a in self._used_axes if a != 'g')
            if 'p' in seq.used_axes:
                self._used_axes = tuple(a for a in self._used_axes if a != 'p')
        if self._mm_config:
            with open(self._folder/'mm_config.txt', 'w') as outfile:
                yaml.dump(self._mm_config, outfile, default_flow_style=False)


    def _create_seq_memmap(
        self, frame: np.ndarray, seq: useq.MDASequence,
    ) -> np.memmap:
        from tifffile import imwrite, memmap

        shape = (
            *tuple(v for k, v in seq.sizes.items() if k in self._used_axes),
            *frame.shape,
        )
        axes = (*self._used_axes, "y", "x")
        dtype = frame.dtype
        # see tifffile.tiffile for more metadata options
        metadata: dict[str, Any] = {"axes": "".join(axes).upper()}
        if seq:
            if seq.time_plan and hasattr(seq.time_plan, "interval"):
                interval = seq.time_plan.interval
                if isinstance(interval, timedelta):
                    interval = interval.total_seconds()
                metadata["TimeIncrement"] = interval
                metadata["TimeIncrementUnit"] = "s"
            if seq.z_plan and hasattr(seq.z_plan, "step"):
                metadata["PhysicalSizeZ"] = seq.z_plan.step
                metadata["PhysicalSizeZUnit"] = "µm"
            if seq.channels:
                metadata["Channel"] = {"Name": [c.config for c in seq.channels]}
        # if acq_date := meta.get("Time"):
        #     metadata["AcquisitionDate"] = acq_date
        # if pix := meta.get("PixelSizeUm"):
        #     metadata["PhysicalSizeX"] = pix
        #     metadata["PhysicalSizeY"] = pix
        #     metadata["PhysicalSizeXUnit"] = "µm"
        #     metadata["PhysicalSizeYUnit"] = "µm"

        # TODO:
        # there's a lot we could still capture, but it comes off the microscope
        # over the course of the acquisition (such as stage positions, exposure times)
        # ... one option is to accumulate these things and then use `tifffile.comment`
        # to update the total metadata in sequenceFinished

        self._mmaps = []
        for g in range(self.n_grid_positions):
            metadata["GridPosition"] = g
            if self.n_grid_positions > 1:
                filename = f"{self._folder.parts[-1]}_g{str(g).zfill(2)}.ome.tiff"
            else:
                filename = f"{self._folder.parts[-1]}.ome.tiff"

            imwrite(Path(self._folder)/filename, shape=shape, dtype=dtype, metadata=metadata)

            # memory map numpy array to data in OME-TIFF file
            _mmap = memmap(Path(self._folder)/filename)
            _mmap = cast("np.memmap", _mmap)
            _mmap = _mmap.reshape(shape)
            self._mmaps.append(_mmap)
        print("MMEPS", len(self._mmaps))
        print(self.n_grid_positions)
        return self._mmaps

    def __del__(self):
        for mmap in self._mmaps:
            mmap.flush()
            del mmap