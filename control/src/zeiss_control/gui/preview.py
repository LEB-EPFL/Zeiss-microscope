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
from vispy import scene, visuals, color
import json

# from pymmcore_widgets._mda._util._hist import HistPlot
from zeiss_control.gui._util.qt_classes import QWidgetRestore

_DEFAULT_WAIT = 20

class Preview(QWidgetRestore):
    new_mask = QtCore.Signal(np.ndarray)

    def __init__(self, parent: QWidget | None = None, mmcore: CMMCorePlus | None = None,
                 key_listener: QObject | None = None):
        super().__init__(parent=parent)
        self._mmc = mmcore
        self.current_frame = None
        settings = self.load_settings()
        self.save_loc = settings.get("path", Path.home())
        # self.rot = settings.get("rot", 90)
        # self.mirror_x = settings.get("mirror_x", False)
        # self.mirror_y = settings.get("mirror_y", True)
        self.rot = 90
        self.mirror_x = False
        self.mirror_y = True

        self.preview = Canvas(mmcore=mmcore, rot=self.rot, mirror_x=self.mirror_x,
                              mirror_y=self.mirror_y, parent=self)
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

    def new_frame(self, image):
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
        self.save_settings(settings)
        super().closeEvent(event)

    def save_settings(self, my_settings):
        file = Path.home() / ".zeiss_control" / "preview.json"
        file.parent.mkdir(parents=True, exist_ok=True)
        with file.open("w") as file:
            json.dump(my_settings, file)
        pass

    def load_settings(self):
        file = Path.home() / ".zeiss_control" / "preview.json"
        try:
            with file.open("r") as file:
                settings_dict = json.load(file)
        except (FileNotFoundError, TypeError, AttributeError, json.decoder.JSONDecodeError) as e:
                print(e)
                print("New Settings for this user")
                settings_dict = {"path": Path.home() / "Desktop" / "MyTiff.ome.tif",
                                 "rot": 0,
                                 "mirror_x": False,
                                 "mirror_y": False}
        return settings_dict


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
        self.current_channel = self._mmc.getConfigGroupState("Channel")

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

        # self.histogram = HistPlot()
        # self.layout().addWidget(self.histogram)

        self.max_slider = 1
        self.clim_slider = QRangeSlider(QtCore.Qt.Horizontal)
        self.clim_slider.setRange(0, self.max_slider)
        self.clim_slider.valueChanged.connect(self.update_clims)

        self.auto_clim = QCheckBox("Auto")
        self.auto_clim.setChecked(True)
        self.auto_clim.stateChanged.connect(self.update_auto)

        self.clim_rectangle_btn = QPushButton("Draw rectangle")
        self.clim_rectangle_btn.setCheckable(True)
        self.clim_rectangle_btn.clicked.connect(self.rect_callback)

        self.clim_layout = QHBoxLayout()
        self.clim_layout.addWidget(self.clim_slider)
        self.clim_layout.addWidget(self.auto_clim)
        self.clim_layout.addWidget(self.clim_rectangle_btn)

        self.layout().addLayout(self.clim_layout)

        #Streaming when live
        self.streaming_timer = QtCore.QTimer(parent=self)
        self.streaming_timer.setTimerType(QtCore.Qt.TimerType.PreciseTimer)
        self.streaming_timer.setInterval(int(self._mmc.getExposure()) or _DEFAULT_WAIT)
        self.streaming_timer.timeout.connect(self._on_image_snapped)

        self._mmc.events.continuousSequenceAcquisitionStarted.connect(self._on_streaming_start)
        self._mmc.events.sequenceAcquisitionStopped.connect(self._on_streaming_stop)
        self._mmc.events.exposureChanged.connect(self._on_exposure_changed)

        #Rect interaction
        self.selected_object = None
        self.selected_point = None
        self.creation_mode = EditRectVisual
        self.objects = []

        self.destroyed.connect(self._disconnect)

    def _disconnect(self) -> None:
        ev = self._mmc.events
        ev.continuousSequenceAcquisitionStarted.disconnect(self._on_streaming_start)
        ev.sequenceAcquisitionStopped.disconnect(self._on_streaming_stop)
        ev.exposureChanged.disconnect(self._on_exposure_changed)

    def _on_exposure_changed(self, device: str, value: str) -> None:
        self.streaming_timer.setInterval(max(20, int(value)))

    def _on_streaming_start(self) -> None:
        self.streaming_timer.start()

    def _on_streaming_stop(self) -> None:
        self.streaming_timer.stop()

    def update_clims(self, value: tuple[int, int]) -> None:
        if not self._clims:
            return
        self.auto_clim.setChecked(False)
        self._clims[self.last_channel] = (value[0], value[1])
        self.image.clim = (value[0], value[1])

    def update_auto(self, state: int) -> None:
        if state == 2:
            self._clim_mode[self.last_channel] = "auto"
        elif state == 0:
            self._clim_mode[self.last_channel] = "manual"

    def _adjust_channel(self, channel: str) -> None:
        if channel == self.last_channel:
            return
        # self.histogram.set_max(self._clims.get(channel, (0, 2))[1])
        block = self.clim_slider.blockSignals(True)
        self.clim_slider.setMaximum(self._clims.get(channel, (0, 2))[1])
        self.clim_slider.blockSignals(block)
        block = self.auto_clim.blockSignals(True)
        self.auto_clim.setChecked(self._clim_mode.get(channel, "auto") == "auto")
        self.auto_clim.blockSignals(block)

    def _on_image_snapped(self, img: np.ndarray | None = None, channel: str|None = None) -> None:
        channel = self._mmc.getCurrentConfig("Channel")
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
            if self.rot == 90:
                trans.translate((img.shape[0], 0, 0))
            elif self.rot == 180:
                trans.translate((img.shape[0], img.shape[1], 0))
            elif self.rot == 270:
                trans.translate((0, img.shape[1], 0))
            print("image rotated by", self.rot)
            self.image.transform = trans
            self.view.camera.set_range(self.image.bounds(0), self.image.bounds(1), margin=0)
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

        #     self.histogram.set_max(slider_max)

        # self.histogram.update_data(img)
        self.last_channel = channel

    # Things for the rectangle
    def rect_callback(self, state):
        if state:
            self.view.camera._viewbox.events.mouse_move.disconnect(
                self.view.camera.viewbox_mouse_event)
            self._canvas.events.mouse_press.connect(self.on_mouse_press) 
            self._canvas.events.mouse_move.connect(self.on_mouse_move) 
        else:
            self.view.camera._viewbox.events.mouse_move.connect(
                self.view.camera.viewbox_mouse_event)  
            self._canvas.events.mouse_press.disconnect(self.on_mouse_press) 
            self._canvas.events.mouse_move.disconnect(self.on_mouse_move)          


    def set_creation_mode(self, object_kind):
        self.creation_mode = object_kind

    def on_mouse_press(self, event):
        tr = self._canvas.scene.node_transform(self.view.scene)
        pos = tr.map(event.pos)
        self.view.interactive = False
        selected = self._canvas.visual_at(event.pos)
        self.view.interactive = True
        if self.selected_object is not None:
            self.selected_object.select(False)
            self.selected_object = None

        if event.button == 1:
            if selected is not None:
                self.selected_object = selected.parent
                # update transform to selected object
                tr = self._canvas.scene.node_transform(self.selected_object)
                pos = tr.map(event.pos)

                self.selected_object.select(True, obj=selected)
                self.selected_object.start_move(pos)
                self.mouse_start_pos = event.pos

            # create new object:
            if self.selected_object is None and self.creation_mode is not None and len(self.objects) == 0:
                # new_object = EditRectVisual(parent=self.view.scene)
                new_object = self.creation_mode(parent=self.view.scene)
                self.objects.append(new_object)
                new_object.select_creation_controlpoint()
                new_object.set_center(pos[0:2])
                self.selected_object = new_object.control_points

        if event.button == 2:  # right button deletes object
            if selected is not None and selected.parent in self.objects:
                self.objects.remove(selected.parent)
                selected.parent.parent = None
                self.selected_object = None

    def on_mouse_move(self, event):
        
        if event.button == 1:
            if self.selected_object is not None:
                self.view.camera._viewbox.events.mouse_move.disconnect(
                    self.view.camera.viewbox_mouse_event)
                # update transform to selected object
                tr = self._canvas.scene.node_transform(self.selected_object)
                pos = tr.map(event.pos)

                self.selected_object.move(pos[0:2])

                mask = np.zeros(self.image.size)
                my_object = self.selected_object
                if not hasattr(my_object, "_center"):
                    my_object = my_object.control_points
                    if isinstance(my_object, list):
                        print("This object has a list of control points")
                        my_object = my_object[0]

                pos = [int(x) for x in my_object._center]
                height = abs(int(my_object._height))
                width = abs(int(my_object._width))
                
                if self.parent().mirror_x:
                    pos[0] = mask.shape[0] - pos[0]
                if self.parent().mirror_y:
                    pos[1] = mask.shape[1] - pos[1]
                if self.parent().rot == 0:
                    pos = [pos[0], mask.shape[1] - pos[1]]
                    width, height = height, width
                    pos[0], pos[1] = pos[1], pos[0]
                elif self.parent().rot == 90:
                    pos = [mask.shape[0] - pos[0], mask.shape[1] - pos[1]]
                elif self.parent().rot == 180:
                    pos = [mask.shape[0] - pos[0], pos[1]]
                    width, height = height, width
                    pos[0], pos[1] = pos[1], pos[0]
                # elif self.parent().rot == 270:
                #     pos = [mask.shape[0] - pos[0], mask.shape[1] - pos[1]]
                mask[int(np.floor(pos[0]-width/2)): int(np.floor(pos[0]+width/2)),
                     int(np.floor(pos[1]-height/2)): int(np.floor(pos[1]+height/2))] = np.ones([width, height])
                self.parent().new_mask.emit(mask)
                # self._on_image_snapped(np.random.random((512, 512)) + mask, "default")
            else:
                self.view.camera._viewbox.events.mouse_move.connect(
                    self.view.camera.viewbox_mouse_event)
        else:
            None



class EditVisual(scene.visuals.Compound):
    def __init__(self, editable=True, selectable=True, on_select_callback=None,
                 callback_argument=None, *args, **kwargs):
        scene.visuals.Compound.__init__(self, [], *args, **kwargs)
        self.unfreeze()
        self.editable = editable
        self._selectable = selectable
        self._on_select_callback = on_select_callback
        self._callback_argument = callback_argument
        self.control_points = ControlPoints(parent=self)
        self.drag_reference = [0, 0]
        self.freeze()

    def add_subvisual(self, visual):
        scene.visuals.Compound.add_subvisual(self, visual)
        visual.interactive = True
        self.control_points.update_bounds()
        self.control_points.visible(False)

    def select(self, val, obj=None):
        if self.selectable:
            self.control_points.visible(val)
            if self._on_select_callback is not None:
                self._on_select_callback(self._callback_argument)

    def start_move(self, start):
        self.drag_reference = start[0:2] - self.control_points.get_center()

    def move(self, end):
        if self.editable:
            shift = end[0:2] - self.drag_reference
            self.set_center(shift)

    def update_from_controlpoints(self):
        None

    @property
    def selectable(self):
        return self._selectable

    @selectable.setter
    def selectable(self, val):
        self._selectable = val

    @property
    def center(self):
        return self.control_points.get_center()

    @center.setter
    # this method redirects to set_center. Override set_center in subclasses.
    def center(self, val):
        self.set_center(val)

    # override this method in subclass
    def set_center(self, val):
        self.control_points.set_center(val[0:2])

    def select_creation_controlpoint(self):
        self.control_points.select(True, self.control_points.control_points[2])


class EditRectVisual(EditVisual):
    def __init__(self, center=[0, 0], width=20, height=20, *args, **kwargs):
        EditVisual.__init__(self, *args, **kwargs)
        self.unfreeze()
        self.rect = scene.visuals.Rectangle(center=center, width=width,
                                            height=height,
                                            color=color.Color("#FFFFFF"),
                                            border_color="red",
                                            border_width=2,
                                            radius=0, parent=self)
        self.rect.interactive = True

        self.freeze()
        self.add_subvisual(self.rect)
        self.control_points.update_bounds()
        self.control_points.visible(False)

    def set_center(self, val):
        self.control_points.set_center(val[0:2])
        self.rect.center = val[0:2]

    def update_from_controlpoints(self):
        self.rect.width = abs(self.control_points._width)
        self.rect.height =abs(self.control_points._height)
        self.rect.center = self.control_points.get_center()



class ControlPoints(scene.visuals.Compound):
    def __init__(self, parent):
        scene.visuals.Compound.__init__(self, [])
        self.unfreeze()
        self.parent = parent
        self._center = [0, 0]
        self._width = 0.0
        self._height = 0.0
        self.selected_cp = None
        self.opposed_cp = None
        self.selected_cp_index = None
        self.opposed_cp_index = None

        self.translate_neighbors = {
            0: [1, 3],
            1: [0, 2],
            2: [3, 1],
            3: [2, 0]
        }

        self.control_points = [scene.visuals.Markers(parent=self)
                               for i in range(0, 4)]
        for c in self.control_points:
            c.set_data(pos=np.array([[0, 0]],
                                    dtype=np.float32),
                       symbol="s",
                       edge_color="red",
                       size=6)
            c.interactive = True
        self.freeze()

    def update_bounds(self):
        pass
        self._center = [0.5 * (self.parent.bounds(0)[1] +
                               self.parent.bounds(0)[0]),
                        0.5 * (self.parent.bounds(1)[1] +
                               self.parent.bounds(1)[0])]
        self._width = max([1, self.parent.bounds(0)[1] - self.parent.bounds(0)[0]])
        self._height = max([1, self.parent.bounds(1)[1] - self.parent.bounds(1)[0]])
        # self.update_points()

    def update_points(self):
        self.control_points[0].set_data(
                pos=np.array([[self._center[0] - 0.5 * self._width,
                            self._center[1] + 0.5 * self._height]]))
        self.control_points[1].set_data(
            pos=np.array([[self._center[0] + 0.5 * self._width,
                        self._center[1] + 0.5 * self._height]]))
        self.control_points[2].set_data(
            pos=np.array([[self._center[0] + 0.5 * self._width,
                        self._center[1] - 0.5 * self._height]]))
        self.control_points[3].set_data(
            pos=np.array([[self._center[0] - 0.5 * self._width,
                        self._center[1] - 0.5 * self._height]]))

    def select(self, val, obj=None):
        self.visible(val)
        self.selected_cp = None
        self.opposed_cp = None

        if obj is not None:
            n_cp = len(self.control_points)
            for i in range(0, n_cp):
                c = self.control_points[i]
                if c == obj:
                    self.selected_cp_index = i
                    self.selected_cp = c
                    self.opposed_cp = \
                        self.control_points[int((i + n_cp / 2)) % n_cp]
                    self.opposed_cp_index = int((i + n_cp / 2)) % n_cp

    def start_move(self, start):
        None

    def move(self, end):
        if not self.parent.editable:
            return
        if self.selected_cp is not None:
            translate = self.translate_neighbors[self.selected_cp_index]

            set_y = self.control_points[self.opposed_cp_index]._data[0][0][1]
            self.control_points[translate[0]].set_data(pos=np.array([[end[0], set_y]]))
            
            set_x = self.control_points[self.opposed_cp_index]._data[0][0][0]
            self.control_points[translate[1]].set_data(pos=np.array([[set_x, end[1]]]))

            self.control_points[self.selected_cp_index].set_data(pos=np.array([[end[0], end[1]]]))

            self._width = self.control_points[0]._data[0][0][0] - self.control_points[3]._data[0][0][0]
            self._height = self.control_points[1]._data[0][0][1] - self.control_points[0]._data[0][0][1]
            self._center[0] = self.control_points[3]._data[0][0][0] + (self.control_points[0]._data[0][0][0] - self.control_points[3]._data[0][0][0]) / 2
            self._center[1] = self.control_points[0]._data[0][0][1] + (self.control_points[2]._data[0][0][1] - self.control_points[0]._data[0][0][1]) / 2

            self.parent.update_from_controlpoints()

    def visible(self, v):
        for c in self.control_points:
            c.visible = v

    def get_center(self):
        return self._center

    def set_center(self, val):
        self._center = val
        self.update_points()


if __name__ == "__main__":
    mmc = CMMCorePlus.instance()
    from qtpy.QtWidgets import QApplication
    app = QApplication([])
    prev = Preview(mmcore=mmc)
    prev.show()
    prev.preview._on_image_snapped(np.random.random((512, 512)), "Default")
    prev.preview.clim_rectangle_btn.click()
    app.exec()