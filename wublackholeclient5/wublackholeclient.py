# This Python file uses the following encoding: utf-8
import os
import sys

from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QMainWindow
from appdirs import user_config_dir

from wublackhole.helper import sizeof_fmt
from wublackhole.wbh_db import WBHDatabase
from wublackholeclient5.client_config import client


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
                    return QIcon('resources/blackhole.svg')
                elif type == '__DIR':
                    return QIcon('resources/folder-clear1.svg')
                else:
                    return QIcon('resources/file-clear1.svg')

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
        uic.loadUi('mainwindow.ui', self)

        # Load settings values to tab
        self.api_le = self.findChild(QtWidgets.QLineEdit, 'api_le')
        self.api_le.setText(client.client['bot']['api'])

        # Load settings values to tab
        save_config_b = self.findChild(QtWidgets.QPushButton, 'save_config_b')
        save_config_b.clicked.connect(self.save_config_b_oncliked)

        # Load settings values to tab
        reset_config_b = self.findChild(QtWidgets.QPushButton, 'reset_config_b')
        reset_config_b.clicked.connect(self.reset_config_b_oncliked)

        # Find the explorer_table
        self.explorer_table = self.findChild(QtWidgets.QTableView, 'explorer_table')
        # Connect double click event
        self.explorer_table.doubleClicked.connect(self.explorer_table_doublecliked)

        # Load Blackholes into explorer
        self.explorer_load_blackholes()


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
        client.client['bot']['api'] = self.api_le.text()
        client.save()


    def reset_config_b_oncliked(self):
        client.load()
        init_database()


def init_database():
    db_filepath = os.path.join(client.config_dirpath, client.client["db_filename"])
    if os.path.exists(db_filepath):
        client.Database = WBHDatabase(db_path=db_filepath,
                                      logger=client.logger_client, echo=True)
    else:
        client.Database = None


def init_confg_dir():
    # Set config directory and file
    client.config_dirpath = user_config_dir("wublackhole")
    client.config_filepath = os.path.join(client.config_dirpath, 'client_config.json')

    if os.path.exists(client.config_dirpath):  # Check if config dir exist
        if os.path.exists(client.config_filepath):  # Check if config file exist
            client.load()  # load config
        else:
            client.init_config()
        # Setup Database
        init_database()
    else:
        client.logger_client.warning("Config directory does not exist `{}`".format(client.config_dirpath))
        os.mkdir(client.config_dirpath)
        client.init_config()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    init_confg_dir()
    window = WUBlackHoleClient()
    window.show()

    # sys.exit(app.exec_())
    # Start the event loop.
    app.exec_()

    sys.exit()
