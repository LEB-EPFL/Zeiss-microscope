"""OME.TIFF writer for MDASequences.
Borrowed from https://github.com/pymmcore-plus/pymmcore-plus/pull/265
Should be replaced once this is merged.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any, cast
from pathlib import Path
import yaml

if TYPE_CHECKING:
    import numpy as np
    import useq


class OMETiffWriter:
    def __init__(self, folder: Path | str, settings:dict | None = None,
                 mm_config: dict|None = None) -> None:
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
        self._settings = settings
        self._mm_config = mm_config

        self._mmaps: None | np.memmap = None
        self._current_sequence: None | useq.MDASequence = None
        self.n_grid_positions: int = 1

    def sequenceStarted(self, seq: useq.MDASequence) -> None:
        self._set_sequence(seq)

    def frameReady(self, frame: np.ndarray, event: useq.MDAEvent, meta: dict) -> None:
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

            mmap = self._create_seq_memmap(frame, seq, meta)[event.index.get("g", 0)]
        else:
            mmap = self._mmaps[event.index.get("g", 0)]

        # WRITE DATA TO DISK
        index = tuple(event.index.get(k) for k in self._used_axes)

        mmap[index] = frame
        mmap.flush()

    # -------------------- private --------------------

    def _set_sequence(self, seq: useq.MDASequence | None) -> None:
        """Set the current sequence, and update the used axes."""
        self._folder.mkdir(parents=True, exist_ok=True)
        self._current_sequence = seq
        if seq:
            self._used_axes = tuple(seq.used_axes)
            if 'g' in seq.used_axes:
                self.n_grid_positions = seq.sizes['g']
                self._used_axes = tuple(a for a in self._used_axes if a != 'g')
        if self._settings:
            with open(self._folder/'isim_settings.yaml', 'w') as outfile:
                yaml.dump(self._settings, outfile, default_flow_style=False)
        if self._mm_config:
            with open(self._folder/'mm_config.txt', 'w') as outfile:
                yaml.dump(self._mm_config, outfile, default_flow_style=False)


    def _create_seq_memmap(
        self, frame: np.ndarray, seq: useq.MDASequence, meta: dict
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
        if acq_date := meta.get("Time"):
            metadata["AcquisitionDate"] = acq_date
        if pix := meta.get("PixelSizeUm"):
            metadata["PhysicalSizeX"] = pix
            metadata["PhysicalSizeY"] = pix
            metadata["PhysicalSizeXUnit"] = "µm"
            metadata["PhysicalSizeYUnit"] = "µm"

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
        return self._mmaps

    def __del__(self):
        for mmap in self._mmaps:
            mmap.flush()
            del mmap