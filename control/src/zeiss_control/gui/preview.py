from __future__ import annotations
from pymmcore_plus import CMMCorePlus
from qtpy.QtWidgets import (QWidget, QGridLayout, QPushButton, QFileDialog, QMainWindow,
                            QVBoxLayout, QHBoxLayout, QCheckBox)
from qtpy import QtCore
from superqt import fonticon, QRangeSlider
from fonticon_mdi6 import MDI6
from tifffile import imsave
from pathlib import Path
import numpy as np
from vispy import scene, visuals
from pymmcore_widgets._mda._util._hist import HistPlot

from isim_control.settings_translate import load_settings, save_settings
from isim_control.gui.assets.qt_classes import QWidgetRestore

class iSIMPreview(QWidgetRestore):
    def __init__(self, parent: QWidget | None = None, mmcore: CMMCorePlus | None = None,
                 key_listener: QObject | None = None):
        super().__init__(parent=parent)
        self._mmc = mmcore
        self.current_frame = None
        settings = self.load_settings()
        self.save_loc = settings.get("path", Path.home())
        self.rot = settings.get("rot", 90)
        self.mirror_x = settings.get("mirror_x", False)
        self.mirror_y = settings.get("mirror_y", True)

        self.preview = Canvas(mmcore=mmcore, rot=self.rot, mirror_x=self.mirror_x,
                              mirror_y=self.mirror_y)
        self._mmc.events.imageSnapped.connect(self.preview._on_image_snapped)
        self._mmc.events.imageSnapped.connect(self.new_frame)

        self.setWindowTitle("Preview")
        self.setLayout(QGridLayout())

        self.layout().addWidget(self.preview, 0, 0, 1, 5)

        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save_image)

        self.collapse_btn = QPushButton()
        self.collapse_btn.setIcon(fonticon.icon(MDI6.arrow_collapse_all))
        self.collapse_btn.clicked.connect(self.collapse_view)

        self.layout().addWidget(self.save_btn, 1, 0)
        self.layout().addWidget(self.collapse_btn, 1, 4)

        if key_listener:
            self.key_listener = key_listener
            self.installEventFilter(self.key_listener)

    def new_frame(self, image, event, meta):
        self.current_frame = image

    def save_image(self):
        if self.current_frame is not None:
            self.save_loc, _ = QFileDialog.getSaveFileName(directory=self.save_loc)
            print(self.save_loc)
            try:
                imsave(self.save_loc[0], self.current_frame)
            except Exception as e:
                import traceback
                print(traceback.format_exc())

    def collapse_view(self):
        self.preview.view.camera.set_range(margin=0)

    def closeEvent(self, event):
        settings = {"path": str(self.save_loc),
                    "rot": self.rot,
                    "mirror_x": self.mirror_x,
                    "mirror_y": self.mirror_y}
        save_settings(settings, "live_view")
        super().closeEvent(event)



class Canvas(QWidget):
    """Copied over from pymmcore_widgets ImagePreview
    """

    def __init__(
        self,
        *,
        parent: QWidget | None = None,
        mmcore: CMMCorePlus | None = None,
        rot: int = 0,
        mirror_x: bool = False,
        mirror_y: bool = False,
    ):
        self.rot = rot
        super().__init__(parent=parent)
        self._mmc = mmcore or CMMCorePlus.instance()
        self._imcls = scene.visuals.Image
        self._clim_mode: dict = {}
        self._clims: dict = {}
        self._cmap: str = "grays"
        self.last_channel = None

        self._canvas = scene.SceneCanvas(
            keys="interactive", size=(512, 512), parent=self
        )
        self.view = self._canvas.central_widget.add_view(camera="panzoom")
        self.view.camera.aspect = 1
        self.view.camera.flip = (mirror_x, mirror_y, False)

        self.image: scene.visuals.Image | None = None
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(self._canvas.native)

        self.histogram = HistPlot()
        self.layout().addWidget(self.histogram)

        self.max_slider = 1
        self.clim_slider = QRangeSlider(QtCore.Qt.Horizontal)
        self.clim_slider.setRange(0, self.max_slider)
        self.clim_slider.valueChanged.connect(self.update_clims)
        self.auto_clim = QCheckBox("Auto")
        self.auto_clim.setChecked(True)
        self.auto_clim.stateChanged.connect(self.update_auto)
        self.clim_layout = QHBoxLayout()
        self.clim_layout.addWidget(self.clim_slider)
        self.clim_layout.addWidget(self.auto_clim)

        self.layout().addLayout(self.clim_layout)

    def update_clims(self, value: tuple[int, int]) -> None:
        if not self._clims:
            return
        self.auto_clim.setChecked(False)
        self._clims[self.last_channel] = (value[0], value[1])

    def update_auto(self, state: int) -> None:
        if state == 2:
            self._clim_mode[self.last_channel] = "auto"
        elif state == 0:
            self._clim_mode[self.last_channel] = "manual"

    def _adjust_channel(self, channel: str) -> None:
        if channel == self.last_channel:
            return
        self.histogram.set_max(self._clims.get(channel, (0, 2))[1])
        block = self.clim_slider.blockSignals(True)
        self.clim_slider.setMaximum(self._clims.get(channel, (0, 2))[1])
        self.clim_slider.blockSignals(block)
        block = self.auto_clim.blockSignals(True)
        self.auto_clim.setChecked(self._clim_mode.get(channel, "auto") == "auto")
        self.auto_clim.blockSignals(block)

    def _on_image_snapped(self, img: np.ndarray | None = None, channel: str|None = None) -> None:
        self._adjust_channel(channel)
        if img is None:
            try:
                img = self._mmc.getLastImage()
            except (RuntimeError, IndexError):
                return
        img_max = img.max()
        #TODO: We might want to do this per channel
        slider_max = max(img_max, self.clim_slider.maximum())
        if self._clim_mode.get(channel, "auto") == "auto":
            clim = (img.min(), img_max)
            self._clims[channel] = clim
        else:
            clim = self._clims.get(channel, (0, 1))
        if self.image is None:
            self.image = self._imcls(
                img, cmap=self._cmap, clim=clim, parent=self.view.scene
            )
            trans = visuals.transforms.linear.MatrixTransform()
            trans.rotate(self.rot, (0, 0, 1))
            trans.translate((img.shape[0], 0, 0))
            print("image rotated by", self.rot)
            self.image.transform = trans
            self.view.camera.set_range(margin=0)
        else:
            self.image.set_data(img)
            self.image.clim = clim
            if self.auto_clim.isChecked():
                block = self.clim_slider.blockSignals(True)
                self.clim_slider.setValue(clim)
                self.clim_slider.blockSignals(block)
        if slider_max > self.clim_slider.maximum():
            block = self.clim_slider.blockSignals(True)
            self.clim_slider.setRange(0, slider_max)
            self.clim_slider.blockSignals(block)
            self.histogram.set_max(slider_max)

        self.histogram.update_data(img)
        self.last_channel = channel