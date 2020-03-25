# This Python file uses the following encoding: utf-8
import os

from PySide2 import QtWidgets
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import QMainWindow, QMessageBox, QDialog

from common.helper import sizeof_fmt
from common.wbh_db import WBHDatabase
from pyclient.client_config import client
from pyclient.restore_backup_window import RestoreBackupWindow


# from PyQt5 import QtWidgets, uic
# from PyQt5.QtCore import *
# from PyQt5.QtGui import *
# from PyQt5.QtWidgets import QApplication
# from PyQt5.QtWidgets import QMainWindow


class TableModel(QAbstractTableModel):
    def __init__(self, data, header):
        super(TableModel, self).__init__()
        self._data = data
        self.header = header


    def data(self, index, role):
        value = self._data[index.row()][index.column()]
        if index.column() == 0:
            type = value
            value = ''
            if role == Qt.DecorationRole:

                if type == '__BH':
                    return QIcon('pyclient/resources/blackhole.svg')
                elif type == '__DIR':
                    return QIcon('pyclient/resources/folder-clear1.svg')
                else:
                    return QIcon('pyclient/resources/file-clear1.svg')

        if role == Qt.DisplayRole:
            # See below for the nested-list data structure.
            # .row() indexes into the outer list,
            # .column() indexes into the sub-list
            # return self._data[index.row()][index.column()]
            return value


    def rowCount(self, index):
        # The length of the outer list.
        return len(self._data)


    def columnCount(self, index):
        # The following takes the first sub-list, and returns
        # the length (only works if all rows are an equal length)
        return len(self._data[0])


    def headerData(self, col, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.header[col]
        return None


class WUBlackHoleClient(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(WUBlackHoleClient, self).__init__(*args, **kwargs)
        # Load the .ui file
        # uic.loadUi('main_window.ui', self)
        ui_file = QFile("pyclient/main_window.ui")
        ui_file.open(QFile.ReadOnly)
        loader = QUiLoader()
        self.window = loader.load(ui_file)

        # Find widgets and connect slots
        self.api_le = self.window.findChild(QtWidgets.QLineEdit, 'api_le')
        self.db_path_le = self.window.findChild(QtWidgets.QLineEdit, 'db_path_le')
        self.db_code_te = self.window.findChild(QtWidgets.QTextEdit, 'db_code_te')
        self.keep_db_sp = self.window.findChild(QtWidgets.QSpinBox, 'keep_db_sp')
        self.client_log_level_cb = self.window.findChild(QtWidgets.QComboBox, 'client_log_level_cb')
        self.bot_log_level_cb = self.window.findChild(QtWidgets.QComboBox, 'bot_log_level_cb')
        save_config_b = self.window.findChild(QtWidgets.QPushButton, 'save_config_b')
        save_config_b.clicked.connect(self.save_config_b_oncliked)
        reset_config_b = self.window.findChild(QtWidgets.QPushButton, 'reset_config_b')
        reset_config_b.clicked.connect(self.reset_config_b_oncliked)
        self.tab_widget = self.window.findChild(QtWidgets.QTabWidget, 'tabWidget')
        self.tab_explorer = self.window.findChild(QtWidgets.QWidget, 'tab_explorer')
        self.explorer_table = self.window.findChild(QtWidgets.QTableView, 'explorer_table')
        self.explorer_table.doubleClicked.connect(self.explorer_table_doublecliked)

        # Load settings tab values from config
        self.reload_settings_tab()

        # Check if there is any Database
        self.check_database_avalibility()

        # Show Window
        self.window.show()


    def reload_settings_tab(self):
        self.api_le.setText(client.client['bot']['api'])
        self.db_path_le.setText(client.client['db_filepath'])
        self.keep_db_sp.setValue(client.client['keep_db_backup'])
        self.client_log_level_cb.setCurrentIndex((client.client['log']['client']['level'] / 10) - 1)
        self.bot_log_level_cb.setCurrentIndex((client.client['log']['bot']['level'] / 10) - 1)


    def check_database_avalibility(self):
        if client.Database:
            # Load Blackholes into explorer
            self.explorer_load_blackholes()
            # Enable Explorer Tab
            self.tab_explorer.setDisabled(False)
            # Switch to Explorer Tab
            self.tab_widget.setCurrentIndex(0)
        else:
            # Disable Explorer Tab
            self.tab_explorer.setDisabled(True)
            # Switch to settings Tab
            self.tab_widget.setCurrentIndex(1)


    def explorer_table_doublecliked(self, clickedIndex: QModelIndex):
        bh_id = self.explorer_table.property('is_blackhole')
        if bh_id is None:
            bh_id = self.explorer_data[clickedIndex.row()][3]
            self.explorer_load_folder(blackhole_id=bh_id, item_id=None)
        else:
            item_id = self.explorer_data[clickedIndex.row()][3]
            self.explorer_load_folder(blackhole_id=bh_id, item_id=item_id)


    def explorer_load_blackholes(self):
        self.explorer_table.setProperty('blackhole_id', None)
        self.explorer_data = []
        if client.Database:
            blackholes = client.Database.get_blackholes()
            bh: WBHDatabase.WBHDbBlackHoles
            for bh in blackholes:
                self.explorer_data.append(['__BH', bh.name, sizeof_fmt(bh.size), bh.id])
            self.model: TableModel = TableModel(data=self.explorer_data, header=[' ', 'Blackhole', 'Total Size', 'ID'])
            self.explorer_table.setModel(self.model)
            for ih in range(len(self.model.header)):
                self.explorer_table.resizeColumnToContents(ih)


    def explorer_load_folder(self, blackhole_id, item_id):
        self.explorer_table.setProperty('is_blackhole', blackhole_id)
        self.explorer_data = []
        if client.Database:
            items = client.Database.get_items_by_parent_id(blackhole_id=blackhole_id, items_parent=item_id)
            itm: WBHDatabase.WBHDbItems
            for itm in items:
                if itm.is_dir:
                    self.explorer_data.append(['__DIR', itm.filename, sizeof_fmt(itm.size), itm.id])
                else:
                    self.explorer_data.append(
                        [os.path.splitext(itm.filename)[1], itm.filename, sizeof_fmt(itm.size), itm.id])
            self.model = TableModel(data=self.explorer_data, header=[' ', 'Name', 'Size', 'ID'])
            self.explorer_table.setModel(self.model)
            for ih in range(len(self.model.header)):
                self.explorer_table.resizeColumnToContents(ih)


    def save_config_b_oncliked(self):
        # Check api
        if len(self.api_le.text()) < 30:
            msg_box = QMessageBox()
            msg_box.warning(self, 'No API', "You have to enter a valid Telegram bot api.")

        # Check db_filepath
        if len(self.db_path_le.text()) < 2:
            msg_box = QMessageBox()
            msg_box.warning(self, 'Invalid Database Path', "You have to enter a valid Database path.")

        # Check database code
        if len(self.db_code_te.toPlainText()) > 0:  # ignore if db code is empty
            if len(self.db_code_te.toPlainText()) < 200:  # a single chunk db is more than 400 characters
                msg_box = QMessageBox()
                msg_box.warning(self, 'Invalid Database Code', "Database code is too short to be valid.")
            else:
                rb_window = RestoreBackupWindow(self.db_code_te.toPlainText())
                self.db_code_te.setPlainText("")

        client.client['bot']['api'] = self.api_le.text()
        client.client['keep_db_backup'] = self.keep_db_sp.value()
        client.client['db_filepath'] = self.db_path_le.text()
        client.client['log']['client']['level'] = (self.client_log_level_cb.currentIndex() + 1) * 10
        client.client['log']['bot']['level'] = (self.bot_log_level_cb.currentIndex() + 1) * 10
        client.save()

        if rb_window.window.result() == QDialog.DialogCode.Accepted:
            # Setup Database
            client.init_database()
            # Check if there is any Database
            self.check_database_avalibility()

    def reset_config_b_oncliked(self):
        client.load()
        # Setup Database
        client.init_database()
        # Setup Bot
        client.init_bot(client.client['bot']['api'], client.client['bot']['proxy'])
        # Load settings tab values from config
        self.reload_settings_tab()
