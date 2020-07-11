# This Python file uses the following encoding: utf-8
import os
from fbs_runtime.application_context.PySide2 import ApplicationContext

import cryptography
from PySide2 import QtWidgets
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import QDialog, QMessageBox

from helper import ChecksumType, EncryptionType, chacha20poly1305_decrypt_data, get_checksum_sha256, \
    get_checksum_sha256_file, get_checksum_sha256_folder, sizeof_fmt
from wbh_db import WBHDatabase, WBHDbItems, WBHDbChunks, WBHDbBlackHoles
from settings import settings

from input_password import InputPasswordDialog
from restore_backup_window import RestoreBackupDialog


# from PyQt5 import QtWidgets, uic
# from PyQt5.QtCore import *
# from PyQt5.QtGui import *
# from PyQt5.QtWidgets import QApplication
# from PyQt5.QtWidgets import QMainWindow

class ExplorerTableProxyModel(QSortFilterProxyModel):
    def __init__(self, *args, **kwargs):
        QSortFilterProxyModel.__init__(self, *args, **kwargs)
        self.filters = {}


    def setFilterByColumn(self, regex, column):
        self.filters[column] = regex
        self.invalidateFilter()


    def filterAcceptsRow(self, source_row, source_parent):
        for key, regex in self.filters.items():
            ix = self.sourceModel().index(source_row, key, source_parent)
            if ix.isValid():
                text = self.sourceModel().data(ix, Qt.DisplayRole)
                # Check if pattern match with text
                if regex.indexIn(text) < 0:
                    return False
        return True


class ExplorerTableModel(QAbstractTableModel):
    def __init__(self, data, header):
        super(ExplorerTableModel, self).__init__()
        self._data = data
        self.header = header


    def data(self, index, role):
        value = self._data[index.row()][index.column()]
        if index.column() == 0:
            type = value
            value = ''
            if role == Qt.DecorationRole:

                if type == '__BH':
                    return QIcon('src/main/resources/blackhole.svg')
                elif type == '__DIR':
                    return QIcon('src/main/resources/folder-clear1.svg')
                else:
                    return QIcon('src/main/resources/file-clear1.svg')

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
        if len(self._data) <= 0:
            return 0
        return len(self._data[0])


    def headerData(self, col, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.header[col]
        return None


class MainWindow(QObject):
    def __init__(self, ui_path, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        # Load the .ui file
        ui_file = QFile(ui_path)
        ui_file.open(QFile.ReadOnly)
        loader = QUiLoader()
        self.window = loader.load(ui_file)

        # base resources path to use for other .ui files
        self.resources_path = os.path.dirname(ui_path)

        # Find widgets and connect slots
        # Server Widgets
        self.backup_pass_le = self.window.findChild(QtWidgets.QLineEdit, 'backup_pass_le')
        self.bh_queue_dirname_le = self.window.findChild(QtWidgets.QLineEdit, 'bh_queue_dirname_le')
        self.chunk_size_sb = self.window.findChild(QtWidgets.QSpinBox, 'chunk_size_sb')
        self.path_check_interval_sb = self.window.findChild(QtWidgets.QSpinBox, 'path_check_interval_sb')
        self.upload_delay_sb = self.window.findChild(QtWidgets.QSpinBox, 'upload_delay_sb')
        # Blackholes Widgets
        self.bh_id_l = self.window.findChild(QtWidgets.QLabel, 'bh_id_l')
        self.bh_path_le = self.window.findChild(QtWidgets.QLineEdit, 'bh_path_le')
        self.bh_name_le = self.window.findChild(QtWidgets.QLineEdit, 'bh_name_le')
        self.bh_tg_id_le = self.window.findChild(QtWidgets.QLineEdit, 'bh_tg_id_le')
        self.encrypt_type_cb = self.window.findChild(QtWidgets.QComboBox, 'encrypt_type_cb')
        self.encrypt_pass_le = self.window.findChild(QtWidgets.QLineEdit, 'encrypt_pass_le')
        # Common Widgets
        self.api_le = self.window.findChild(QtWidgets.QLineEdit, 'api_le')
        self.db_path_le = self.window.findChild(QtWidgets.QLineEdit, 'db_path_le')
        self.temp_path_le = self.window.findChild(QtWidgets.QLineEdit, 'temp_path_le')
        self.bh_queue_dirname_le = self.window.findChild(QtWidgets.QLineEdit, 'bh_queue_dirname_le')
        self.db_code_te = self.window.findChild(QtWidgets.QTextEdit, 'db_code_te')
        self.keep_db_sp = self.window.findChild(QtWidgets.QSpinBox, 'keep_db_sp')
        self.max_dl_retry_sb = self.window.findChild(QtWidgets.QSpinBox, 'max_dl_retry_sb')
        self.client_log_level_cb = self.window.findChild(QtWidgets.QComboBox, 'client_log_level_cb')
        self.bot_log_level_cb = self.window.findChild(QtWidgets.QComboBox, 'bot_log_level_cb')
        # Settings Buttons
        save_config_b = self.window.findChild(QtWidgets.QPushButton, 'save_config_b')
        save_config_b.clicked.connect(self.on_save_config_b_clicked)
        reset_config_b = self.window.findChild(QtWidgets.QPushButton, 'reset_config_b')
        reset_config_b.clicked.connect(self.on_reset_config_b_cliked)
        # Tabs
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
        self.dl_progress_folder = self.window.findChild(QtWidgets.QProgressBar, 'dl_progress_folder')
        self.dl_progress_folder.setVisible(False)
        self.filter_le = self.window.findChild(QtWidgets.QLineEdit, 'filter_le')
        self.filter_le.textChanged.connect(self.on_filter_le_text_changed)

        # Load settings tab values from config
        self.reload_settings_tab()

        # Check if there is any Database
        self.check_database_avalibility()


    def reload_settings_tab(self):
        self.backup_pass_le.setText(settings.config['server']['backup_pass'])
        self.bh_queue_dirname_le.setText(settings.config['server']['blackhole_queue_dirname'])
        self.chunk_size_sb.setValue(int(settings.config['server']['chunk_size']))
        self.path_check_interval_sb.setValue(int(settings.config['server']['path_check_interval']))
        self.upload_delay_sb.setValue(int(settings.config['server']['upload_delay']))

        self.bh_id_l.setText(settings.config['blackhole'][0]['id'])
        self.bh_path_le.setText(settings.config['blackhole'][0]['dirpath'])
        self.bh_name_le.setText(settings.config['blackhole'][0]['name'])
        self.bh_tg_id_le.setText(settings.config['blackhole'][0]['telegram_id'])
        # self.encrypt_type_cb.setCurrentIndex((int(settings.config['blackhole'][0]['encryption_type'])) - 1)
        self.encrypt_type_cb.setCurrentText(settings.config['blackhole'][0]['encryption_type'])
        self.encrypt_pass_le.setText(settings.config['blackhole'][0]['encryption_pass'])

        self.api_le.setText(settings.config['telegram']['api'])
        self.db_path_le.setText(settings.config['general']['db_filepath'])
        self.temp_path_le.setText(settings.config['general']['tempdir'])
        self.keep_db_sp.setValue(int(settings.config['general']['keep_db_backup']))
        self.max_dl_retry_sb.setValue(int(settings.config['general']['max_download_retry']))
        self.client_log_level_cb.setCurrentIndex((int(settings.config['general']['log_level']) / 10) - 1)
        self.bot_log_level_cb.setCurrentIndex((int(settings.config['telegram']['log_level']) / 10) - 1)


    def check_database_avalibility(self):
        pass
        if settings.Database:
            # Load Blackholes into explorer
            self.explorer_load_blackholes()
            # Enable Explorer Tab
            self.tab_explorer.setDisabled(False)
            # Switch to Explorer Tab
            self.tab_widget.setCurrentIndex(0)
        else:
            # clear address bar
            self.addressbar_clear()
            # Disable Explorer Tab
            self.tab_explorer.setDisabled(True)
            # Switch to settings Tab
            self.tab_widget.setCurrentIndex(2)


    def explorer_load_blackholes(self):
        self.explorer_table.setProperty('blackhole_id', None)
        self.explorer_data = []

        # # clear address bar
        self.addressbar_clear()

        if settings.Database:
            blackholes = settings.Database.get_blackholes()
            bh: WBHDbBlackHoles
            for bh in blackholes:
                self.explorer_data.append(['__BH', bh.name, sizeof_fmt(bh.size), bh.id])
            self.explorer_model = ExplorerTableModel(data=self.explorer_data,
                                                     header=[' ', 'Blackhole', 'Total Size', 'ID'])
            self.explorer_proxy_model = ExplorerTableProxyModel(self)
            self.explorer_proxy_model.setSourceModel(self.explorer_model)
            self.explorer_table.setModel(self.explorer_proxy_model)
            for ih in range(len(self.explorer_model.header)):
                self.explorer_table.resizeColumnToContents(ih)
            self.addressbar_add(name="ROOT", db_id=-2, blackhole_id=None)


    def explorer_load_folder(self, blackhole_id, item_id):
        self.explorer_table.setProperty('blackhole_id', blackhole_id)
        self.explorer_data = []
        if settings.Database:
            items = settings.Database.get_items_by_parent_id(blackhole_id=blackhole_id, items_parent=item_id)
            itm: WBHDbItems
            for itm in items:
                if itm.is_dir:
                    self.explorer_data.append([
                        '__DIR',
                        itm.filename,
                        sizeof_fmt(itm.size),
                        itm.id,
                        itm.uploaded_at.strftime("%Y-%m-%d %H:%M:%S"),
                        "{} items".format(itm.items_count),
                        itm.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                        itm.modified_at.strftime("%Y-%m-%d %H:%M:%S")
                    ])
                else:
                    self.explorer_data.append([
                        os.path.splitext(itm.filename)[1],
                        itm.filename,
                        sizeof_fmt(itm.size),
                        itm.id,
                        itm.uploaded_at.strftime("%Y-%m-%d %H:%M:%S"),
                        "{} parts".format(itm.chunks_count),
                        itm.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                        itm.modified_at.strftime("%Y-%m-%d %H:%M:%S")
                    ])
            self.explorer_model = ExplorerTableModel(data=self.explorer_data, header=[
                ' ',
                'Name',
                'Size',
                'ID',
                'Uploaded',
                'Contain',
                'Created',
                'Modified'
            ])
            self.explorer_proxy_model = ExplorerTableProxyModel(self)
            self.explorer_proxy_model.setSourceModel(self.explorer_model)
            self.explorer_table.setModel(self.explorer_proxy_model)
            selection = self.explorer_table.selectionModel()
            selection.currentChanged.connect(self.on_explorer_table_current_changed)
            for ih in range(len(self.explorer_model.header)):
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
                # blackhole_id = self.explorer_data[clickedIndex.row()][3]  # get blackhole id
                blackhole_id = clickedIndex.siblingAtColumn(3).data()  # get blackhole id
                # self.addressbar_add(name=self.explorer_data[clickedIndex.row()][1], db_id=-1, blackhole_id=blackhole_id)
                self.addressbar_add(name=clickedIndex.siblingAtColumn(1).data(), db_id=-1, blackhole_id=blackhole_id)
                self.explorer_load_folder(blackhole_id=blackhole_id, item_id=None)
            else:
                # Loading a folder in blackhole blackhole_id
                # item_id = self.explorer_data[clickedIndex.row()][3]  # get item id
                item_id = clickedIndex.siblingAtColumn(3).data()  # get item id
                # self.addressbar_add(name=self.explorer_data[clickedIndex.row()][1], db_id=item_id,
                self.addressbar_add(name=clickedIndex.siblingAtColumn(1).data(), db_id=item_id,
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


    def on_filter_le_text_changed(self, text: str):
        self.explorer_proxy_model.setFilterByColumn(QRegExp(text, Qt.CaseInsensitive, QRegExp.RegExp), 1)
        pass


    def on_download_pb_cliked(self):
        # Disable UI
        self.tab_widget.setDisabled(True)
        self.dl_progress.setVisible(True)
        self.filter_le.setVisible(False)
        # Get selected row
        selected_row = self.explorer_table.selectedIndexes()
        # Ask where to save
        if selected_row[0].data(100) == "__DIR":
            # Directory
            self.dl_progress_folder.setVisible(True)
            dirpath = QtWidgets.QFileDialog.getExistingDirectory(self.window, 'Save to folder', selected_row[1].data())
            QCoreApplication.processEvents()  # to avoid QFileDialog stay open because of GUI delay
            if len(dirpath) > 3:
                self.download_folder(item_id=selected_row[3].data(),
                                     blackhole_id=self.explorer_table.property('blackhole_id'),
                                     save_to=dirpath)
        else:
            # File
            filepath = QtWidgets.QFileDialog.getSaveFileName(self.window, 'Save file', selected_row[1].data(),
                                                             "All Files (*.*)")
            QCoreApplication.processEvents()  # to avoid QFileDialog stay open because of GUI delay
            if len(filepath[0]) > 3:
                self.download_file(item_id=selected_row[3].data(),
                                   blackhole_id=self.explorer_table.property('blackhole_id'),
                                   save_to=filepath[0])
        # Re-enable UI
        self.tab_widget.setDisabled(False)
        self.dl_progress.setVisible(False)
        self.dl_progress_folder.setVisible(False)
        self.filter_le.setVisible(True)


    def on_save_config_b_clicked(self):
        # Check BlackHole Path
        if not os.path.exists(self.bh_path_le.text()):
            msg_box = QMessageBox()
            msg_box.critical(self.window, 'Invalid BlackHole Path', "You have to enter a valid/existing path.")
            return

        # Check Backup Password
        if len(self.backup_pass_le.text()) < 6:
            msg_box = QMessageBox()
            msg_box.critical(self.window, 'Invalid Backup Password', "Backup password should be at least 6 characters.")
            return

        # Check API
        if len(self.api_le.text()) < 30:
            msg_box = QMessageBox()
            msg_box.critical(self.window, 'No API', "You have to enter a valid Telegram bot api.")
            return

        # Check db_filepath
        if len(self.db_path_le.text()) < 2:
            msg_box = QMessageBox()
            msg_box.critical(self.window, 'Invalid Database Path', "You have to enter a valid Database path.")
            return

        # Check bh_queue_dirname_le
        if len(self.bh_queue_dirname_le.text()) < 2:
            msg_box = QMessageBox()
            msg_box.critical(self.window, 'Invalid Queue Dir Name', "You have to enter a valid Queue Dir Name.")
            return

        # Check temp_path_le
        if len(self.temp_path_le.text()) < 2:
            msg_box = QMessageBox()
            msg_box.critical(self.window, 'Invalid TempDir', "You have to enter a valid TempDir.")
            return

        # Check database code
        if len(self.db_code_te.toPlainText()) > 0:  # ignore if db code is empty
            if len(self.db_code_te.toPlainText()) < 200:  # a single chunk db is more than 400 characters
                msg_box = QMessageBox()
                msg_box.warning(self.window, 'Invalid Database Code', "Database code is too short to be valid.")
            else:
                # Close database file to avoid file lock on windows
                settings.Database.Session.close_all()
                settings.Database.conn.close()
                # Show dialog
                rb_window = RestoreBackupDialog(self.db_code_te.toPlainText(),
                                                ui_path=os.path.join(self.resources_path, "restore_backup_window.ui"))
                self.db_code_te.setPlainText("")

        settings.config['server']['backup_pass'] = self.backup_pass_le.text()
        settings.config['server']['blackhole_queue_dirname'] = self.bh_queue_dirname_le.text()
        settings.config['server']['chunk_size'] = str(self.chunk_size_sb.value())
        settings.config['server']['path_check_interval'] = str(self.path_check_interval_sb.value())
        settings.config['server']['upload_delay'] = str(self.upload_delay_sb.value())

        settings.config['blackhole'][0]['dirpath'] = self.bh_path_le.text()
        settings.config['blackhole'][0]['name'] = self.bh_name_le.text()
        settings.config['blackhole'][0]['telegram_id'] = self.bh_tg_id_le.text()
        settings.config['blackhole'][0]['encryption_type'] = self.client_log_level_cb.currentText()
        settings.config['blackhole'][0]['encryption_pass'] = self.encrypt_pass_le.text()

        settings.config['telegram']['api'] = self.api_le.text()
        settings.config['general']['keep_db_backup'] = str(self.keep_db_sp.value())
        settings.config['general']['max_download_retry'] = str(self.max_dl_retry_sb.value())
        settings.config['general']['db_filepath'] = self.db_path_le.text()
        settings.config['general']['tempdir'] = self.temp_path_le.text()
        settings.config['general']['blackhole_queue_dirname'] = self.bh_queue_dirname_le.text()
        settings.config['general']['log_level'] = str((self.client_log_level_cb.currentIndex() + 1) * 10)
        settings.config['telegram']['log_level'] = str((self.bot_log_level_cb.currentIndex() + 1) * 10)
        settings.save()

        if 'rb_window' in locals():
            if rb_window.window.result() == QDialog.DialogCode.Accepted:
                # Setup Database
                settings.init_database()
                # Check if there is any Database
                self.check_database_avalibility()


    def on_reset_config_b_cliked(self):
        # client.load()
        # # Setup Database
        # client.init_database()
        # # Setup Bot
        # client.init_bot(settings.config['telegram']['log_level'], client.client['bot']['proxy'])
        # Load settings tab values from config
        self.reload_settings_tab()


    def dl_progress_update(self, wrote_size: int, total_size: int):
        percentage = int((wrote_size * 100) / total_size)
        self.dl_progress.setValue(percentage)
        self.dl_progress.setFormat(
            "{}/{}   {}%".format(sizeof_fmt(wrote_size, 1), sizeof_fmt(total_size, 1), percentage))
        self.dl_progress.repaint()
        QCoreApplication.processEvents()  # force process events because of GUI delay


    def dl_progress_folder_update(self, wrote_size: int, total_size: int):
        percentage = int((wrote_size * 100) / total_size)
        self.dl_progress_folder.setValue(percentage)
        self.dl_progress_folder.setFormat(
            "{}/{}   {}%".format(sizeof_fmt(wrote_size, 1), sizeof_fmt(total_size, 1), percentage))
        self.dl_progress_folder.repaint()
        QCoreApplication.processEvents()  # force process events because of GUI delay


    def ask_for_rewrite(self, path) -> bool:
        return QMessageBox.question(self.window, "Rewrite ?", "Following path exist. "
                                                              "Are you sure you want to rewrite on it?"
                                                              "\n`{}`".format(path),
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)


    def download_folder(self, item_id, blackhole_id, save_to, db_item: WBHDbItems = None,
                        ask_rewrite: bool = True, use_msg_box: bool = True):
        no_error = True
        # try:
        #     # Get item from Database if did not presented
        #     if db_item is None:
        #         db_item = client.Database.get_item_by_id(blackhole_id=blackhole_id, item_id=item_id)
        #         self.dl_progress_folder.setProperty('wrote_size', 0)
        #         self.dl_progress_folder.setProperty('total_size', db_item.size)
        #     # update progressbar to set initial text
        #     self.dl_progress_folder_update(0, self.dl_progress_folder.property('total_size'))
        #     # prepare new folder path
        #     new_dirpath = os.path.join(save_to, db_item.filename)
        #     # check if exist and ask for rewrite
        #     if ask_rewrite and use_msg_box:
        #         if os.path.exists(new_dirpath):
        #             if self.ask_for_rewrite(new_dirpath) == QMessageBox.No:
        #                 return
        #             else:
        #                 ask_rewrite = False
        #     os.makedirs(new_dirpath, exist_ok=True)
        #     client.logger_client.debug("Create new folder: `{}`".format(new_dirpath))
        #     itm: WBHDbItems
        #     for itm in db_item.items:
        #         if itm.is_dir:
        #             no_error = no_error & self.download_folder(item_id=item_id, blackhole_id=blackhole_id,
        #                                                        save_to=new_dirpath, db_item=itm,
        #                                                        ask_rewrite=ask_rewrite)
        #         else:
        #             new_filepath = os.path.join(new_dirpath, itm.filename)
        #             no_error = no_error & self.download_file(item_id=item_id, blackhole_id=blackhole_id,
        #                                                      save_to=new_filepath, db_item=itm,
        #                                                      ask_rewrite=ask_rewrite, use_msg_box=False)
        #             self.dl_progress_folder.setProperty('wrote_size',
        #                                                 self.dl_progress_folder.property('wrote_size') + itm.size)
        #         self.dl_progress_folder_update(self.dl_progress_folder.property('wrote_size'),
        #                                        self.dl_progress_folder.property('total_size'))
        #
        #     if db_item.id == item_id:  # original download request
        #         # Match file checksum
        #         if db_item.checksum_type == ChecksumType.SHA256.value:
        #             db_item_checksum = get_checksum_sha256_folder(dirpath=new_dirpath)
        #             if db_item_checksum == db_item.checksum:
        #                 client.logger_client.debug("{} checksum for `{}` matched."
        #                                            .format(ChecksumType(db_item.checksum_type).name,
        #                                                    db_item.filename))
        #                 # Folder Downloaded Correctly
        #                 if use_msg_box:
        #                     msg_box = QMessageBox()
        #                     msg_box.information(self.window, 'Download',
        #                                         "Folder successfully downloaded:\n`{}`".format(new_dirpath))
        #                 return no_error
        #             else:
        #                 raise Exception("Mismatch checksum for `{}`".format(db_item.filename))
        #     return no_error
        # except Exception as e:
        #     client.logger_client.error("Can not download folder by id `{}`\n\n{}".format(item_id, str(e)))
        #     if use_msg_box:
        #         msg_box = QMessageBox()
        #         msg_box.critical(self.window, 'Error',
        #                          "Can not download folder by id `{}`\n\n{}".format(item_id, str(e)))
        return False


    def download_file(self, item_id, blackhole_id, save_to, db_item: WBHDbItems = None,
                      ask_rewrite: bool = True, use_msg_box: bool = True):
        # try:
        #     is_error = 0
        #     wrote_size = 0
        #     # check if exist and ask for rewrite
        #     if ask_rewrite and use_msg_box:
        #         if os.path.exists(save_to):
        #             if self.ask_for_rewrite(save_to) == QMessageBox.No:
        #                 return
        #             else:
        #                 ask_rewrite = False
        #     # Get item from Database if did not presented
        #     if db_item is None:
        #         db_item = client.Database.get_item_by_id(blackhole_id=blackhole_id, item_id=item_id)
        #     # update progressbar to set initial text
        #     self.dl_progress_update(0, db_item.size)
        #     # Open file to write
        #     with open(save_to, 'wb') as item_f:
        #         chunk: WBHDbChunks
        #         for chunk in db_item.chunks:
        #             # Download chunk
        #             chunk_filepath = os.path.join(client.tempdir, chunk.filename)
        #             download_retry = 0
        #             while True:
        #                 if client.TelegramBot.get_chunk(chunk, chunk_filepath):
        #                     with open(chunk_filepath, 'rb') as chunk_f:
        #                         chunk_data = chunk_f.read()
        #                         client.logger_client.debug(
        #                             "Read {} from chunk#{}".format(sizeof_fmt(len(chunk_data)), chunk.index))
        #                         if chunk.encryption == EncryptionType.ChaCha20Poly1305.value:
        #                             client.logger_client.debug(
        #                                 "Decrypting {} ...".format(EncryptionType.ChaCha20Poly1305.name))
        #                             # Extract key and nonce from encryption_data
        #                             chunk_key_hex, chunk_nonce_hex = chunk.encryption_data.split('O')
        #                             # ask for password if never asked
        #                             if client.password is None:
        #                                 ip_dialog = InputPasswordDialog(os.path.join(self.resources_path, "input_password.ui"), EncryptionType(chunk.encryption))
        #                                 if ip_dialog.window.result() == QDialog.DialogCode.Rejected:
        #                                     # User didn't entered password, CANCEL
        #                                     client.logger_client.warning("Aborted by user.")
        #                                     is_error = 2
        #                                     break
        #                                 else:
        #                                     client.password = ip_dialog.encryption_pass
        #                                 QCoreApplication.processEvents()  # force process events because of GUI delay
        #                             # Decrypt chunk
        #                             chunk_data = chacha20poly1305_decrypt_data(data=chunk_data,
        #                                                                        secret=client.password.encode(),
        #                                                                        key=bytes.fromhex(chunk_key_hex),
        #                                                                        nonce=bytes.fromhex(chunk_nonce_hex))
        #                         # Matching Checksums
        #                         if chunk.checksum_type == ChecksumType.NONE.value:
        #                             client.logger_client.debug("There is no checksum for chunk#{}".format(chunk.index))
        #                         if chunk.checksum_type == ChecksumType.SHA256.value:
        #                             chunk_checksum = get_checksum_sha256(chunk_data)
        #                             if chunk_checksum == chunk.checksum:
        #                                 client.logger_client.debug("{} checksum for chunk#{} matched."
        #                                                            .format(ChecksumType(chunk.checksum_type).name,
        #                                                                    chunk.index))
        #                             else:
        #                                 raise Exception("ERROR: {} checksum for chunk#{} mismatched.".format(
        #                                     ChecksumType(chunk.checksum_type).name, chunk.index))
        #                         # Write to file
        #                         item_f.write(chunk_data)
        #                         client.logger_client.debug("Wrote {} to file `{}`"
        #                                                    .format(sizeof_fmt(len(chunk_data)),
        #                                                            os.path.split(save_to)[1]))
        #                         wrote_size += len(chunk_data)
        #                         self.dl_progress_update(wrote_size, db_item.size)
        #                         break
        #                 elif download_retry < settings.config['client']['max_download_retry']:
        #                     # Retry to download. Timeout happens a lot while downloading
        #                     download_retry += 1
        #                     client.logger_client.warning(
        #                         "Retrying to download chunk#{} by name of `{}` from BlackHole ({}/{})..."
        #                             .format(chunk.index, chunk.filename, download_retry,
        #                                     settings.config['client']['max_download_retry']))
        #                 else:
        #                     raise Exception(
        #                         "Could not download chunk#{} by name of `{}` from BlackHole after {} retries."
        #                             .format(chunk.index, chunk.filename, download_retry))
        #
        #             # Remove chunk file if exist
        #             if os.path.exists(chunk_filepath):
        #                 os.remove(chunk_filepath)
        #
        #         if is_error == 0:
        #             # Match file checksum
        #             if db_item.checksum_type == ChecksumType.SHA256.value:
        #                 db_item_checksum = get_checksum_sha256_file(filepath=save_to)
        #                 if db_item_checksum == db_item.checksum:
        #                     client.logger_client.debug("{} checksum for `{}` matched."
        #                                                .format(ChecksumType(db_item.checksum_type).name,
        #                                                        db_item.filename))
        #                     # File Downloaded Correctly
        #                     if use_msg_box:
        #                         msg_box = QMessageBox()
        #                         msg_box.information(self.window, 'Download',
        #                                             "File successfully downloaded:\n`{}`".format(save_to))
        #                     return True
        #                 else:
        #                     raise Exception("Mismatch checksum for `{}`".format(db_item.filename))
        # except cryptography.exceptions.InvalidTag:
        #     client.logger_client.error("Incorrect password.")
        #     client.password = None
        #     if use_msg_box:
        #         msg_box = QMessageBox()
        #         msg_box.critical(self.window, 'Error', "Password is incorrect.")
        # except Exception as e:
        #     client.logger_client.error("Can not download file by id `{}`\n\n{}".format(item_id, str(e)))
        #     if use_msg_box:
        #         msg_box = QMessageBox()
        #         msg_box.critical(self.window, 'Error', "Can not download file by id `{}`\n\n{}".format(item_id, str(e)))

        return False
