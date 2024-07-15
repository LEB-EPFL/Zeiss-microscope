"""Customized Qt classes for overall GUI behaviour."""

from qtpy import QtWidgets, QtCore


class QMainWindowRestore(QtWidgets.QMainWindow):
    """QMainWindow that saves its last position to the registry and loads it when opened again.

    Also closes all the other windows that are open in the application.
    """

    def __init__(self, parent=None):
        """Load the settings in the registry an reset position. If no present, use default."""
        super().__init__(parent=parent)
        self.qt_settings = QtCore.QSettings("EDA", self.__class__.__name__)
        # Initial window size/pos last saved. Use default values for first time
        self.resize(self.qt_settings.value("size", QtCore.QSize(270, 225)))
        self.move(self.qt_settings.value("pos", QtCore.QPoint(50, 50)))

    def closeEvent(self, e):
        """Write window size and position to config file."""
        self.qt_settings.setValue("size", self.size())
        self.qt_settings.setValue("pos", self.pos())
        # Close all other windows too
        app = QtWidgets.QApplication.instance()
        app.closeAllWindows()
        e.accept()


class QWidgetRestore(QtWidgets.QWidget):
    """QWidget that saves its last position to the registry and loads it when opened again.

    Also closes all the other windows that are open in the application.
    """

    def __init__(self, parent=None, close_all=False):
        """Load the settings in the registry an reset position. If no present, use default."""
        super().__init__(parent=parent)
        self.close_all = close_all
        self.qt_settings = QtCore.QSettings("EDA", self.__class__.__name__)
        # Initial window size/pos last saved. Use default values for first time
        self.resize(self.qt_settings.value("size", QtCore.QSize(270, 225)))
        self.move(self.qt_settings.value("pos", QtCore.QPoint(50, 50)))

    def closeEvent(self, e):
        """Write window size and position to config file."""
        self.qt_settings.setValue("size", self.size())
        self.qt_settings.setValue("pos", self.pos())
        # Close all other windows too
        if self.close_all:
            app = QtWidgets.QApplication.instance()
            app.closeAllWindows()
            e.accept()
        else:
            super().closeEvent(e)
