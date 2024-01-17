from pymmcore_widgets._mda import MDAWidget
from pymmcore_plus import CMMCorePlus
from qtpy.QtWidgets import QCheckBox, QLineEdit, QHBoxLayout
from qtpy.QtCore import Signal, QEvent, QSize, QPoint, QSettings
from pathlib import Path
import json
from useq import MDASequence
import re



class ZeissMDAWidget(MDAWidget):
    "Adding save information and events to the MDAWidget"
    new_save_settings = Signal(bool, str)
    mda_settings_event = Signal(object)
    def __init__(self, mmcore:CMMCorePlus,
                 save_filename: str="settings",
                 include_run_button:bool=True,
                 saving:bool=True):
        super().__init__(mmcore=mmcore, include_run_button=include_run_button)
        self.saving = saving
        if saving:
            self.save = QCheckBox("Save")
            self.save.stateChanged.connect(self.new_save_settings_set)
            self.path = QLineEdit("Path")
            self.path.textChanged.connect(self.new_save_settings_set)
            self.save_box = QHBoxLayout()
            self.save_box.addWidget(self.save)
            self.save_box.addWidget(self.path)
            self.layout().insertLayout(1, self.save_box)
            self._mmc.mda.events.sequenceFinished.connect(self.on_sequence_finished)


        self.settings_file = Path.home() / ".zeiss_control" / f"{save_filename}.json"
        self.saving_file = Path.home() / ".zeiss_control" / "saving.json"

        self.settings, self.saving = self.load_settings()
        self.set_state(self.settings)

        self._tab.installEventFilter(self)

        self.qt_settings = QSettings("EDA", self.__class__.__name__ + save_filename)
        # Initial window size/pos last saved. Use default values for first time
        self.resize(self.qt_settings.value("size", QSize(270, 225)))
        self.move(self.qt_settings.value("pos", QPoint(50, 50)))


    def on_sequence_finished(self):
        "Increment the saving file name"

        if "ome.tiff" in self.path.text():
            sub_string = re.search(r"_\d{2,5}\.ome\.tiff", self.path.text())
            number = int(sub_string.group(0)[1:4])
            self.path.setText(self.path.text().replace(sub_string.group(0), f"_{number + 1:03}.ome.tiff"))
        else:
            sub_strings = self.path.text().split("_")
            number = int(sub_strings[-1])
            self.path.setText("_".join(sub_strings[:-1] + [str(number + 1).zfill(3)]))



    def new_save_settings_set(self):
        self.new_save_settings.emit(self.save.isChecked(), self.path.text())

    def save_settings(self):
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
        self.settings = self.get_state().json()
        with open(self.settings_file, "w") as file:
            json.dump(self.settings, file)
        # Saving
        if self.saving:
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
            settings_dict = re.sub(r"stage_positions\": \[.*?\]", "stage_positions\": []", settings_dict)
            settings = MDASequence().parse_raw(settings_dict)
            if self.saving:
                with self.saving_file.open("r") as file:
                    savings_dict = json.load(file)
                if savings_dict == {}:
                    raise FileNotFoundError
                self.save.setChecked(savings_dict['save'])
                self.path.setText(savings_dict['path'])
            else:
                savings_dict = {}
        except (FileNotFoundError, TypeError, AttributeError, json.decoder.JSONDecodeError) as e:
            print(e)
            print("New Settings for this user")
            settings = MDASequence()
            savings_dict = {'save': True, "path": str(Path.home() / 'Desktop/FOV_000.ome.tiff')}

        return settings, savings_dict

    def closeEvent(self, e):
        self.save_settings()
        self.qt_settings.setValue("size", self.size())
        self.qt_settings.setValue("pos", self.pos())
        return super().closeEvent(e)

    def send_new_settings(self):
        self.mda_settings_event.emit(self.get_state())

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Leave:
            print(event)
            self.mda_settings_event.emit(self.get_state())
        return super().eventFilter(obj, event)
