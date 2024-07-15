from qtpy.QtWidgets import QApplication
from pymmcore_plus import CMMCorePlus
from pymmcore_widgets import MDAWidget

from zeiss_control.gui.preview import Preview
from zeiss_control.gui.main import MainWindow

app = QApplication([])

mmc = CMMCorePlus()

#TODO: what is going on here?
try:
    mmc.loadSystemConfiguration("C:/Control_2/Zeiss-microscope/240715_ZeissAxioObserver7.cfg")
except OSError:
    mmc.loadSystemConfiguration("C:/Control_2/Zeiss-microscope/240715_ZeissAxioObserver7.cfg")

preview = Preview(mmcore=mmc)
preview.show()

main = MainWindow(mmc)
main.show()

mda = MDAWidget(mmcore=mmc)
mda.show()


app.exec_()