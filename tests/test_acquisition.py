from pymmcore_plus import CMMCorePlus
from pymmcore_plus.mda.handlers import OMEZarrWriter
from pymmcore_plus.mda import mda_listeners_connected
from useq import MDASequence

from pathlib import Path
import shutil


mmc = CMMCorePlus()
mmc.loadSystemConfiguration("C:/Control_2/Zeiss-microscope/240715_ZeissAxioObserver7.cfg")
seq = MDASequence(time_plan={'interval': 1, 'loops': 5},
                channels=[{"config": "Brightfield", "exposure": 100}])

def test_brightfield_acq():
    mmc.mda.run(seq)

def test_zarr_writer():
    path = "./data/test.ome.zarr"
    writer = OMEZarrWriter(path, overwrite=True)

    with mda_listeners_connected(writer):
        mmc.mda.run(seq)
    
    assert Path(path).is_dir()
    shutil.rmtree(path)