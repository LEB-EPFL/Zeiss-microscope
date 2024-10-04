from __future__ import annotations
from pymmcore_plus import CMMCorePlus
from pymmcore_widgets._stack_viewer_v2 import MDAViewer
from ndv import DataWrapper
from useq import MDASequence
from pymmcore_widgets._stack_viewer_v2._data_wrapper import MM5DWriter



# class OuputGUI():
#     def __init__(self, mmc: CMMCorePlus):
#         self.mmc = mmc
#         self.mmc.mda.events.sequenceStarted.connect(self.sequenceStarted)

#     def sequenceStarted(self, sequence: MDASequence, meta):
        
#         self.mmc.mda.toggle_pause()
#         self.viewer = MDAViewer()
#         self.viewer.show()

#         self.viewer.data.sequenceStarted(sequence, meta)
#         self.mmc.mda.events.sequenceFinished.connect(self.viewer.data.sequenceFinished)
#         self.mmc.mda.events.frameReady.connect(self.viewer.data.frameReady)
#         self.mmc.mda.toggle_pause()

#     def sequenceFinished(self):
#         self.mmc.mda.events.sequenceFinished.disconnect(self.viewer.data.sequenceFinished)
#         self.mmc.mda.events.frameReady.disconnect(self.viewer.data.frameReady)
#         self.mmc.mda.events.sequenceStarted.disconnect(self.viewer.data.sequenceStarted)
#         self.viewer = None
