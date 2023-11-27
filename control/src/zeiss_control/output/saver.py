"""OME.TIFF writer for MDASequences.
Borrowed from https://github.com/pymmcore-plus/pymmcore-plus/pull/265
Should be replaced once this is merged.
"""

from __future__ import annotations
from pymmcore_plus import CMMCorePlus

from zeiss_control.output.datastore import QLocalDataStore

from datetime import timedelta
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from pathlib import Path

    import numpy as np
    import useq


class CoreOMETiffWriter:
    def __init__(self, filename: Path | str, mmcore: CMMCorePlus,
                 datastore: QLocalDataStore) -> None:
        try:
            import tifffile  # noqa: F401
        except ImportError as e:  # pragma: no cover
            raise ImportError(
                "tifffile is required to use this handler. "
                "Please `pip install tifffile`."
            ) from e

        # create an empty OME-TIFF file
        self._filename = filename
        self._mmap: None | np.memmap = None
        self._mmc = mmcore
        self.datastore = datastore

        self._mmc.mda.events.sequenceStarted.connect(self.sequenceStarted)
        self.datastore.frame_ready.connect(self.frameReady)

    def sequenceStarted(self, seq: useq.MDASequence) -> None:
        self._set_sequence(seq)

    def frameReady(self, event: useq.MDAEvent,) -> None:
        index = (event.index.get("t", 0), event.index.get("z", 0), event.index.get("c", 0))
        frame = self.datastore.get_frame(index)
        if event is None:
            return
        if self._mmap is None:
            if not self._current_sequence:
                # just in case sequenceStarted wasn't called
                self._set_sequence(event.sequence)  # pragma: no cover

            if not (seq := self._current_sequence):
                raise NotImplementedError(
                    "Writing zarr without a MDASequence not yet implemented"
                )

            mmap = self._create_seq_memmap(frame, seq)
        else:
            mmap = self._mmap

        # WRITE DATA TO DISK
        index = tuple(event.index.get(k) for k in self._used_axes)

        mmap[index] = frame
        mmap.flush()

    # -------------------- private --------------------

    def _set_sequence(self, seq: useq.MDASequence | None) -> None:
        """Set the current sequence, and update the used axes."""
        self._current_sequence = seq
        try:
            if seq:
                self._used_axes = tuple(seq.used_axes)
        except:
            self._used_axes = ('T', 'C')


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



        # TODO:
        # there's a lot we could still capture, but it comes off the microscope
        # over the course of the acquisition (such as stage positions, exposure times)
        # ... one option is to accumulate these things and then use `tifffile.comment`
        # to update the total metadata in sequenceFinished
        imwrite(self._filename, shape=shape, dtype=dtype, metadata=metadata)

        # memory map numpy array to data in OME-TIFF file
        self._mmap = memmap(self._filename)
        self._mmap = cast("np.memmap", self._mmap)
        self._mmap = self._mmap.reshape(shape)
        return self._mmap