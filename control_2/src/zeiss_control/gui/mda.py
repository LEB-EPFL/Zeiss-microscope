# from pymmcore_widgets._stack_viewer_v2._mda_viewer import MDAViewer
from pymmcore_widgets import MDAWidget
from pymmcore_plus.mda.handlers import OMEZarrWriter

from pymmcore_plus import CMMCorePlus
from qtpy.QtCore import Signal, QSize, QPoint, QSettings
from pathlib import Path
import json
from useq import MDASequence
import pydantic_core


class ZeissMDAWidget(MDAWidget):
    "Adding save information and events to the MDAWidget"
    def __init__(self, mmcore:CMMCorePlus,
                 save_filename: str="settings"):
        
        super().__init__(mmcore=mmcore)
        self.settings_file = Path.home() / ".zeiss_control" / f"{save_filename}.json"
        self.saving_file = Path.home() / ".zeiss_control" / "saving.json"
        self.settings, self.saving = self.load_settings()
        self.setValue(self.settings)

        self.qt_settings = QSettings("EDA", self.__class__.__name__ + save_filename)
        # Initial window size/pos last saved. Use default values for first time
        self.resize(self.qt_settings.value("size", QSize(270, 225)))
        self.move(self.qt_settings.value("pos", QPoint(50, 50)))

    def run_mda(self):
        save_path = self.prepare_mda()
        if save_path is False:
            return
        handler = OMEZarrWriter(save_path)
        sequence = self.value()
        handler.sequenceStarted(sequence, sequence.metadata)
        # self.viewer = MDAViewer(handler)
        # self.viewer.show()
        self.execute_mda(handler)

#--- TAKE the next to out if they are implemented in the main branch

    def prepare_mda(self) -> bool|str|None:
        """Prepare the MDA sequence experiment."""
        # in case the user does not press enter after editing the save name.
        self.save_info.save_name.editingFinished.emit()

        # if autofocus has been requested, but the autofocus device is not engaged,
        # and position-specific offsets haven't been set, show a warning
        pos = self.stage_positions
        if (
            self.af_axis.value()
            and not self._mmc.isContinuousFocusLocked()
            and (not self.tab_wdg.isChecked(pos) or not pos.af_per_position.isChecked())
            and not self._confirm_af_intentions()
        ):
            return False

        # technically, this is in the metadata as well, but isChecked is more direct
        if self.save_info.isChecked():
            return self._update_save_path_from_metadata(
                self.value(), update_metadata=True
            )
        else:
            return None

    def execute_mda(self, output: Path | str | object | None) -> None:
        """Execute the MDA experiment corresponding to the current value"""
        sequence = self.value()
        # run the MDA experiment asynchronously
        self._mmc.run_mda(sequence, output=output)


    def save_settings(self):
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
        self.settings = self.value()
        with open(self.settings_file, "w") as file:
            file.write(self.settings.model_dump_json(indent=2))
        # Saving
        self.saving_file.parent.mkdir(parents=True, exist_ok=True)
        self.saving = self.save_info.value()
        with open(self.saving_file, "w") as file:
            json.dump(self.saving, file)

    def load_settings(self):
        try:
            settings = MDASequence.from_file(self.settings_file)
            settings = settings.replace(stage_positions=[])
        except (FileNotFoundError, pydantic_core._pydantic_core.ValidationError, json.decoder.JSONDecodeError):
            print("Error loading settings")
            settings = MDASequence()
        try:
            with self.saving_file.open("r") as file:
                savings_dict = json.load(file)
            if savings_dict == {}:
                savings_dict = {"save_dir": "", "save_name": "", "format": "ome-tiff", "should_save": False,}
            self.save_info.setValue(savings_dict)
        except FileNotFoundError:
            savings_dict = {"save_dir": "", "save_name": "", "format": "ome-tiff", "should_save": False,}
        return settings, savings_dict

    def closeEvent(self, e):
        self.save_settings()
        self.qt_settings.setValue("size", self.size())
        self.qt_settings.setValue("pos", self.pos())
        return super().closeEvent(e)


