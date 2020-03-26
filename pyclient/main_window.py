# This Python file uses the following encoding: utf-8
import os

import cryptography
from PySide2 import QtWidgets
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import QDialog, QMainWindow, QMessageBox

from common.helper import ChecksumType, EncryptionType, chacha20poly1305_decrypt_data, get_checksum_sha256, \
    get_checksum_sha256_file, sizeof_fmt
from common.wbh_db import WBHDatabase
from pyclient.client_config import client
from pyclient.input_password import InputPasswordDialog
from pyclient.restore_backup_window import RestoreBackupDialog


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

            if role == 100:
                return type

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


class ClientMainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(ClientMainWindow, self).__init__(*args, **kwargs)
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
        save_config_b.clicked.connect(self.on_save_config_b_cliked)
        reset_config_b = self.window.findChild(QtWidgets.QPushButton, 'reset_config_b')
        reset_config_b.clicked.connect(self.on_reset_config_b_cliked)
        self.tab_widget = self.window.findChild(QtWidgets.QTabWidget, 'tabWidget')
        self.tab_explorer = self.window.findChild(QtWidgets.QWidget, 'tab_explorer')
        self.explorer_table = self.window.findChild(QtWidgets.QTableView, 'explorer_table')
        self.explorer_table.doubleClicked.connect(self.on_explorer_table_doublecliked)
        self.address_bar_hl = self.window.findChild(QtWidgets.QHBoxLayout, 'address_bar_hl')
        self.button_group = QtWidgets.QButtonGroup(parent=self.tab_explorer)
        self.button_group.buttonClicked[int].connect(self.on_address_bar_clicked)
        self.download_pb = self.window.findChild(QtWidgets.QPushButton, 'download_pb')
        self.download_pb.clicked.connect(self.on_download_pb_cliked)
        self.dl_progress = self.window.findChild(QtWidgets.QProgressBar, 'dl_progress')
        self.dl_progress.setVisible(False)

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
            # clear addressbar
            self.addressbar_clear()
            # Disable Explorer Tab
            self.tab_explorer.setDisabled(True)
            # Switch to settings Tab
            self.tab_widget.setCurrentIndex(1)


    def explorer_load_blackholes(self):
        self.explorer_table.setProperty('blackhole_id', None)
        self.explorer_data = []

        # # clear address bar
        self.addressbar_clear()

        if client.Database:
            blackholes = client.Database.get_blackholes()
            bh: WBHDatabase.WBHDbBlackHoles
            for bh in blackholes:
                self.explorer_data.append(['__BH', bh.name, sizeof_fmt(bh.size), bh.id])
            self.model: TableModel = TableModel(data=self.explorer_data, header=[' ', 'Blackhole', 'Total Size', 'ID'])
            self.explorer_table.setModel(self.model)
            for ih in range(len(self.model.header)):
                self.explorer_table.resizeColumnToContents(ih)
            self.addressbar_add(name="ROOT", db_id=-2, blackhole_id=None)


    def explorer_load_folder(self, blackhole_id, item_id):
        self.explorer_table.setProperty('blackhole_id', blackhole_id)
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
            selection = self.explorer_table.selectionModel()
            selection.currentChanged.connect(self.on_explorer_table_current_changed)
            for ih in range(len(self.model.header)):
                self.explorer_table.resizeColumnToContents(ih)


    def addressbar_clear(self):
        for button in self.button_group.buttons():
            self.button_group.removeButton(button)
            self.address_bar_hl.removeWidget(button)
            button.close()


    def addressbar_add(self, name, db_id, blackhole_id):
        btn = QtWidgets.QPushButton(text=name, parent=self.tab_explorer)
        btn.setProperty('db_id', db_id)
        btn.setProperty('blackhole_id', blackhole_id)
        btn.adjustSize()
        btn.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        # Add button to ButtonGroup
        self.button_group.addButton(btn, db_id)
        # insert widget before the last one (last one is space expander)
        self.address_bar_hl.insertWidget(self.address_bar_hl.count() - 1, btn)


    def on_explorer_table_current_changed(self, current: QModelIndex, previous: QModelIndex):
        if current.siblingAtColumn(0).data(100) == "__BH":
            self.download_pb.setDisabled(True)
        else:
            self.download_pb.setDisabled(False)


    def on_explorer_table_doublecliked(self, clickedIndex: QModelIndex):
        if clickedIndex.siblingAtColumn(0).data(100) == "__BH" or clickedIndex.siblingAtColumn(0).data(100) == "__DIR":
            blackhole_id = self.explorer_table.property('blackhole_id')
            if blackhole_id is None:
                # Loading root of blackhole
                blackhole_id = self.explorer_data[clickedIndex.row()][3]  # get blackhole id
                self.addressbar_add(name=self.explorer_data[clickedIndex.row()][1], db_id=-1, blackhole_id=blackhole_id)
                self.explorer_load_folder(blackhole_id=blackhole_id, item_id=None)
            else:
                # Loading a folder in blackhole blackhole_id
                item_id = self.explorer_data[clickedIndex.row()][3]  # get item id
                self.addressbar_add(name=self.explorer_data[clickedIndex.row()][1], db_id=item_id,
                                    blackhole_id=blackhole_id)
                self.explorer_load_folder(blackhole_id=blackhole_id, item_id=item_id)


    def on_address_bar_clicked(self, btn_id):
        found = False
        target_btn = self.button_group.button(btn_id)
        # Remove all buttons after target button
        for button in self.button_group.buttons():
            if found:
                self.button_group.removeButton(button)
                self.address_bar_hl.removeWidget(button)
                button.close()
            else:
                if button is target_btn:
                    found = True

        if target_btn.property('db_id') < 0:
            if target_btn.property('blackhole_id') is None:  # ROOT
                self.explorer_load_blackholes()
            else:  # Root of blackhole
                self.explorer_load_folder(blackhole_id=target_btn.property('blackhole_id'),
                                          item_id=None)
        else:  # folder
            self.explorer_load_folder(blackhole_id=target_btn.property('blackhole_id'),
                                      item_id=target_btn.property('db_id'))


    def on_download_pb_cliked(self):
        # Disable UI
        self.tab_widget.setDisabled(True)
        self.dl_progress.setVisible(True)
        # Get selected row
        selected_row = self.explorer_table.selectedIndexes()
        # Ask where to save
        if selected_row[0].data() == "__DIR":
            # Directory
            QMessageBox().information(self, "", "Not Implemented yet!")
            pass
        else:
            # File
            filepath = QtWidgets.QFileDialog.getSaveFileName(self.window, 'Save file', selected_row[1].data(),
                                                             "All Files (*.*)")
            self.download_file(item_id=selected_row[3].data(),
                               blackhole_id=self.explorer_table.property('blackhole_id'),
                               save_to=filepath[0])
            # Re-enable UI
            self.tab_widget.setDisabled(False)
            self.dl_progress.setVisible(False)


    def on_save_config_b_cliked(self):
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
                rb_window = RestoreBackupDialog(self.db_code_te.toPlainText())
                self.db_code_te.setPlainText("")

        client.client['bot']['api'] = self.api_le.text()
        client.client['keep_db_backup'] = self.keep_db_sp.value()
        client.client['db_filepath'] = self.db_path_le.text()
        client.client['log']['client']['level'] = (self.client_log_level_cb.currentIndex() + 1) * 10
        client.client['log']['bot']['level'] = (self.bot_log_level_cb.currentIndex() + 1) * 10
        client.save()

        if 'rb_window' in locals():
            if rb_window.window.result() == QDialog.DialogCode.Accepted:
                # Setup Database
                client.init_database()
                # Check if there is any Database
                self.check_database_avalibility()


    def on_reset_config_b_cliked(self):
        client.load()
        # Setup Database
        client.init_database()
        # Setup Bot
        client.init_bot(client.client['bot']['api'], client.client['bot']['proxy'])
        # Load settings tab values from config
        self.reload_settings_tab()


    def dl_progress_update(self, wrote_size: int, total_size: int):
        percentage = int((wrote_size * 100) / total_size)
        self.dl_progress.setValue(percentage)
        self.dl_progress.setFormat(
            "{}/{}   {}%".format(sizeof_fmt(wrote_size, 1), sizeof_fmt(total_size, 1), percentage))
        self.repaint()


    def download_file(self, item_id, blackhole_id, save_to):
        try:
            password = None
            is_error = 0
            wrote_size = 0
            # Get item from Database
            db_item = client.Database.get_item_by_id(blackhole_id=blackhole_id, item_id=item_id)
            # update progressbar to set initial text
            self.dl_progress_update(0, db_item.size)
            # Open file to write
            with open(save_to, 'wb') as item_f:
                chunk: WBHDatabase.WBHDbChunks
                for chunk in db_item.chunks:
                    # Download chunk
                    chunk_filepath = os.path.join(client.tempdir, chunk.filename)
                    if client.TelegramBot.get_chunk(chunk, chunk_filepath):
                        with open(chunk_filepath, 'rb') as chunk_f:
                            chunk_data = chunk_f.read()
                            client.logger_client.debug(
                                "Read {} from chunk#{}".format(sizeof_fmt(len(chunk_data)), chunk.index))
                            if chunk.encryption == EncryptionType.ChaCha20Poly1305.value:
                                # ask for encryption if never asked
                                if password is None:
                                    ip_dialog = InputPasswordDialog(EncryptionType(chunk.encryption))
                                    if ip_dialog.window.result() == QDialog.DialogCode.Rejected:
                                        # User didn't entered password, CANCEL
                                        client.logger_client.warning("Aborted by user.")
                                        is_error = 2
                                        break
                                client.logger_client.debug(
                                    "Decrypting {} ...".format(EncryptionType.ChaCha20Poly1305.name))
                                # Extract key and nonce from encryption_data
                                chunk_key_hex, chunk_nonce_hex = chunk.encryption_data.split('O')
                                password = ip_dialog.encryption_pass
                                # Decrypt chunk
                                chunk_data = chacha20poly1305_decrypt_data(data=chunk_data,
                                                                           secret=password.encode(),
                                                                           key=bytes.fromhex(chunk_key_hex),
                                                                           nonce=bytes.fromhex(chunk_nonce_hex))
                            # Matching Checksums
                            if chunk.checksum_type == ChecksumType.NONE.value:
                                client.logger_client.debug("There is no checksum for chunk#{}".format(chunk.index))
                            if chunk.checksum_type == ChecksumType.SHA256.value:
                                chunk_checksum = get_checksum_sha256(chunk_data)
                                if chunk_checksum == chunk.checksum:
                                    client.logger_client.debug("{} checksum for chunk#{} matched."
                                                               .format(ChecksumType(chunk.checksum_type).name,
                                                                       chunk.index))
                                else:
                                    raise Exception("ERROR: {} checksum for chunk#{} mismatched.".format(
                                        ChecksumType(chunk.checksum_type).name, chunk.index))
                            # Write to file
                            item_f.write(chunk_data)
                            client.logger_client.debug("Wrote {} to file `{}`"
                                                       .format(sizeof_fmt(len(chunk_data)), os.path.split(save_to)[1]))
                            wrote_size += len(chunk_data)
                            self.dl_progress_update(wrote_size, db_item.size)
                    else:
                        raise Exception("Could not download chunk#{} by name of `{}` from BlackHole"
                                        .format(chunk.index, chunk.filename))

                if is_error == 0:
                    # Match file checksum
                    if db_item.checksum_type == ChecksumType.SHA256.value:
                        db_item_checksum = get_checksum_sha256_file(filepath=save_to)
                        if db_item_checksum == db_item.checksum:
                            client.logger_client.debug("{} checksum for `{}` matched."
                                                       .format(ChecksumType(db_item.checksum_type).name,
                                                               db_item.filename))
                            # File Downloaded Correctly
                            msg_box = QMessageBox()
                            msg_box.information(self, 'Download', "File successfully downloaded:\n`{}`".format(save_to))
                        else:
                            raise Exception("Mismatch checksum for `{}`".format(db_item.filename))
        except cryptography.exceptions.InvalidTag:
            client.logger_client.error("Incorrect password for chunk#{}".format(chunk.index))
            msg_box = QMessageBox()
            msg_box.critical(self, 'Error', "Password is incorrect.")
        except Exception as e:
            client.logger_client.error("Can not download file by id `{}`\n\n{}".format(item_id, str(e)))
            msg_box = QMessageBox()
            msg_box.critical(self, 'Error', "Can not download file by id `{}`\n\n{}".format(item_id, str(e)))
