from __future__ import annotations

import copy
from typing import TYPE_CHECKING

import numpy as np
import numpy.typing as npt
from pymmcore_plus import CMMCorePlus
from qtpy import QtCore, QtGui
from qtpy.QtCore import Signal
from useq import MDAEvent
from eda_plugin.utility.core_event_bus import CoreEventBus

if TYPE_CHECKING:
    from qtpy.QtWidgets import QWidget

DIMENSIONS = ["t", "c", "z"]


class QLocalDataStore(QtCore.QObject):
    """Connects directly to mmcore frameReady and saves the data in a numpy array."""

    frame_ready = Signal(MDAEvent)

    def __init__(
        self,
        shape: tuple[int, ...],
        dtype: npt.DTypeLike = np.uint16,
        parent: QWidget | None = None,
        mmcore: CMMCorePlus | None = None,
        eda_event_bus: CoreEventBus | None = None,
    ):
        super().__init__(parent=parent)
        self.dtype = np.dtype(dtype)
        self.array: np.ndarray = np.ndarray(shape, dtype=self.dtype)

        self._mmc: CMMCorePlus = mmcore or CMMCorePlus.instance()
        self.eda_event_bus: CoreEventBus = eda_event_bus

        self.listener = self.EventListener(self._mmc, self.eda_event_bus, self.array.shape[2])
        self.listener.start()
        self.listener.frame_ready.connect(self.new_frame)

    class EventListener(QtCore.QThread):
        """Receive events in a separate thread."""

        frame_ready = Signal(np.ndarray, MDAEvent)

        def __init__(self, mmcore: CMMCorePlus, eda_event_bus: CoreEventBus = None,
                     channels: int = None):
            super().__init__()
            self._mmc = mmcore
            self._mmc.mda.events.frameReady.connect(self.on_frame_ready)
            self.channels = channels
            if eda_event_bus:
                self.eda_event_bus = eda_event_bus
                self.eda_event_bus.new_network_image.connect(self.on_network_image)

        def on_frame_ready(self, img: np.ndarray, event: MDAEvent) -> None:
            self.frame_ready.emit(img, event)

        def on_network_image(self, img: np.ndarray, timepoint: tuple):
            # print("NETWORK IMAGE IN DATASTORE", img.min(), img.max())
            event = MDAEvent(channel={"config": "Network"}, index={'t': timepoint[0], 'c': self.channels-1})
            self.frame_ready.emit(img, event)

        def closeEvent(self, event: QtGui.QCloseEvent) -> None:
            self._mmc.mda.events.frameReady.disconnect(self.on_frame_ready)
            super().exit()
            event.accept()

    def new_frame(self, img: np.ndarray, event: MDAEvent) -> None:
        self.shape = img.shape
        indices = self.complement_indices(event)
        # print("ADDING IMAGE TO DATASTORE", img.max())
        try:
            self.array[
                indices["t"], indices["z"], indices["c"], indices.get("g", 0), :, :
            ] = img
        except IndexError:
            self.correct_shape(indices)
            self.new_frame(img, event)
            return
        # print("ADDED IMAGE TO DATASTORE", img.max(), indices)
        self.frame_ready.emit(event)

    def get_frame(self, key: tuple) -> np.ndarray:
        print(key)
        return np.array(self.array[key])

    def complement_indices(self, event: MDAEvent | dict) -> dict:
        indices = dict(copy.deepcopy(dict(event.index)))
        for i in DIMENSIONS:
            if i not in indices:
                indices[i] = 0
        return indices

    def correct_shape(self, indices: dict) -> None:
        """The initialised shape does not fit the data, extend the array."""
        min_shape = [indices["t"], indices["z"], indices["c"], indices.get("g", 0)]
        diff = [x - y + 1 for x, y in zip(min_shape, self.array.shape[:-2])]
        for i, app in enumerate(diff):
            if app > 0:
                if i == 0:  # handle time differently, double the size
                    app = max(self.array.shape[0], 1)
                append_shape = [*self.array.shape[:i], app, *self.array.shape[i + 1 :]]
                self.array = np.append(
                    self.array, np.zeros(append_shape, self.array.dtype), axis=i
                )

    def __del__(self) -> None:
        self.listener.exit()
        self.listener.wait()
