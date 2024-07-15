
import pyqtgraph as pg
from pyqtgraph.graphicsItems.PlotCurveItem import PlotCurveItem
from qtpy import QtCore
from eda_plugin.utility.core_event_bus import CoreEventBus

class EventScorePlot(pg.PlotWidget):
    """Displays output of an analyser over time and the decision parameters of the interpreter."""

    def __init__(self, event_bus: CoreEventBus, *args, **kwargs):
        """Initialise the main plot and the horizontal lines showing the thresholds.

        The lines are used to show the current parameters of a BinaryFrameRateInterpreter.
        """
        super().__init__(*args, **kwargs)
        self.event_bus = event_bus

        #TODO: Make this function
        # self.qt_settings = QSettings("EDA", self.__class__.__name__ + save_filename)
        # # Initial window size/pos last saved. Use default values for first time
        # self.resize(self.qt_settings.value("size", QSize(270, 225)))
        # self.move(self.qt_settings.value("pos", QPoint(50, 50)))

        self.output_line = PlotCurveItem([], pen="w")
        self.output_scatter = pg.ScatterPlotItem([], symbol="o", pen=None)

        self.thresholds = [80, 100]
        pen = pg.mkPen(color="#FF0000", style=QtCore.Qt.DashLine)
        self.thrLine1 = pg.InfiniteLine(pos=80, angle=0, pen=pen)
        self.thrLine2 = pg.InfiniteLine(pos=100, angle=0, pen=pen)
        self.addItem(self.thrLine1)
        self.addItem(self.thrLine2)
        self.addItem(self.output_line)
        self.addItem(self.output_scatter)
        self.enableAutoRange()
        pg.setConfigOptions(antialias=True)
        self.setWindowTitle("EventScore")

        self.x_data = []
        self.y_data = []

        self.event_bus.acquisition_started_event.connect(self._reset_plot)
        self.event_bus.new_decision_parameter.connect(self.add_datapoint)
        self.event_bus.new_parameters.connect(self._set_thr_lines)

    def add_datapoint(self, y: float, x: float, _):
        """Add a datapoint that is received from the analyser."""
        self.x_data.append(x)
        self.y_data.append(y)
        self._refresh_plot()

    def _refresh_plot(self):
        self.output_line.setData(self.x_data, self.y_data)
        self.output_scatter.setData(self.x_data, self.y_data)
        self.enableAutoRange()

    def _reset_plot(self):
        self.x_data = []
        self.y_data = []
        self._refresh_plot()


    def _set_thr_lines(self, params):
        try:
            self.thrLine1.setPos(params.lower_threshold)
            self.thrLine2.setPos(params.upper_threshold)
        except AttributeError:
            self.thrLine1.setPos(params.get('lower_threshold', 0.7))
            self.thrLine2.setPos(params.get('upper_threshold', 0.9))        

    # def closeEvent(self, e):
    #     # self.save_settings()
    #     self.qt_settings.setValue("size", self.size())
    #     self.qt_settings.setValue("pos", self.pos())
    #     return super().closeEvent(e)