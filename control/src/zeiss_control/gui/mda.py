from pymmcore_widgets._mda import MDAWidget
from pymmcore_plus import CMMCorePlus
from qtpy.QtWidgets import QCheckBox, QLineEdit, QHBoxLayout
from qtpy.QtCore import Signal, QEvent
from pathlib import Path
import json
import yaml
from useq import MDASequence
import re
import logging


class ZeissMDAWidget(MDAWidget):
    "Adding save information to the MDAWidget"
    new_save_settings = Signal(bool, str)
    mda_settings_event = Signal(object)
    def __init__(self, mmcore:CMMCorePlus):
        super().__init__(mmcore=mmcore, include_run_button=True)

        self.save = QCheckBox("Save")
        self.save.stateChanged.connect(self.new_save_settings_set)
        self.path = QLineEdit("Path")
        self.path.textChanged.connect(self.new_save_settings_set)

        self.save_box = QHBoxLayout()
        self.save_box.addWidget(self.save)
        self.save_box.addWidget(self.path)

        self.layout().insertLayout(1, self.save_box)

        self.settings_file = Path.home() / ".zeiss_control" / "settings.json"
        self.saving_file = Path.home() / ".zeiss_control" / "saving.json"

        self.settings, self.saving = self.load_settings()
        self.set_state(self.settings)

        self._mmc.mda.events.sequenceFinished.connect(self.on_sequence_finished)

        self._tab.installEventFilter(self)


    def on_sequence_finished(self):
        "Increment the saving file name"
        sub_string = re.search(r"_\d{2,5}\.ome\.tiff", self.path.text())
        number = int(sub_string.group(0)[1:4])
        self.path.setText(self.path.text().replace(sub_string.group(0), f"_{number + 1:03}.ome.tiff"))

    def new_save_settings_set(self):
        self.new_save_settings.emit(self.save.isChecked(), self.path.text())

    def save_settings(self):
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
        self.settings = self.get_state().json()
        with open(self.settings_file, "w") as file:
            json.dump(self.settings, file)
        # Saving
        self.saving_file.parent.mkdir(parents=True, exist_ok=True)
        self.saving = {'save': self.save.isChecked(), "path": self.path.text()}
        with open(self.saving_file, "w") as file:
            json.dump(self.saving, file)

    def load_settings(self):
        try:
            with self.settings_file.open("r") as file:
                settings_dict = json.load(file)
            if settings_dict == {}:
                raise FileNotFoundError
            print(settings_dict)
            print(settings_dict.__class__)
            settings_dict = re.sub(r"stage_positions\": \[.*?\]", "stage_positions\": []", settings_dict)
            print(settings_dict)
            settings = MDASequence().parse_raw(settings_dict)
            
            with self.saving_file.open("r") as file:
                savings_dict = json.load(file)
            if savings_dict == {}:
                raise FileNotFoundError
            self.save.setChecked(savings_dict['save'])
            self.path.setText(savings_dict['path'])
        except (FileNotFoundError, TypeError, AttributeError, json.decoder.JSONDecodeError) as e:
            print(e)
            print("New Settings for this user")
            settings = MDASequence()
            savings_dict = {'save': True, "path": str(Path.home() / 'Desktop/FOV_000.ome.tiff')}

        return settings, savings_dict
    
    def closeEvent(self, e):
        self.save_settings()
        return super().closeEvent(e)
    
    def send_new_settings(self):
        self.mda_settings_event.emit(self.get_state())

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Leave:
            print(event)
            self.mda_settings_event.emit(self.get_state())
        return super().eventFilter(obj, event)
    
