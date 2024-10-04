from qtpy.QtWidgets import QApplication
from pymmcore_plus import CMMCorePlus
from pymmcore_widgets import MDAWidget

from zeiss_control.gui.preview import Preview
from zeiss_control.gui.main import MainWindow
from zeiss_control.gui.mda import ZeissMDAWidget
from zeiss_control.backend.meta import MetaDataWriter
from zeiss_control.smart_spatial.smart_engine import SmartEngine
# from zeiss_control.gui.viewers import OuputGUI

app = QApplication([])

mmc = CMMCorePlus()

#TODO: what is going on here?
try:
    mmc.loadSystemConfiguration("C:/Control_2/Zeiss-microscope/240715_ZeissAxioObserver7.cfg")
except OSError:
    import time
    time.sleep(2)
    mmc.loadSystemConfiguration("C:/Control_2/Zeiss-microscope/240715_ZeissAxioObserver7.cfg")

engine = SmartEngine(mmc)
mmc.mda.set_engine(engine)

mmc.setChannelGroup("Channel")
preview = Preview(mmcore=mmc)
preview.show()

main = MainWindow(mmc)
main.show()

mda = MDAWidget(mmcore=mmc)
mda.show()
# This can be deleted if pymmcore-plus handles tiff metadata correctly
metadatawriter = MetaDataWriter(mda, mmc)

# viewers = OuputGUI(mmc)


app.exec_()