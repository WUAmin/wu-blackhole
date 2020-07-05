# This Python file uses the following encoding: utf-8
import os
import shutil
import time
from datetime import datetime

from PySide2 import QtWidgets, QtCore
from PySide2.QtCore import *
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import QDialog

from helper import ChecksumType, EncryptionType, chacha20poly1305_decrypt_data, \
    decompress_bytes_to_string_b64zlib, get_checksum_sha256, sizeof_fmt


class InputPasswordDialog(QObject):
    def __init__(self, ui_path, encryption_type: EncryptionType = None, *args, **kwargs):
        super(InputPasswordDialog, self).__init__(*args, **kwargs)
        # Load the .ui file
        ui_file = QFile(ui_path)
        ui_file.open(QFile.ReadOnly)
        loader = QUiLoader()
        self.window = loader.load(ui_file)

        self.encryption_type = encryption_type
        self.encryption_pass = None

        # Find widgets
        self.encryption_type_cb = self.window.findChild(QtWidgets.QComboBox, 'encryption_type_cb')
        self.encryption_pass_le = self.window.findChild(QtWidgets.QLineEdit, 'encryption_pass_le')
        self.ok_pb = self.window.findChild(QtWidgets.QPushButton, 'ok_pb')
        self.ok_pb.clicked.connect(self.ok_pb_clicked)
        self.cancel_pb = self.window.findChild(QtWidgets.QPushButton, 'cancel_pb')
        self.cancel_pb.clicked.connect(self.cancel_pb_clicked)

        # Load all supported encryptions
        for e_type in EncryptionType:
            self.encryption_type_cb.addItem(e_type.name, e_type.value)

        # If Encryption presented
        if encryption_type:
            self.encryption_type_cb.setCurrentIndex(self.encryption_type_cb.findText(encryption_type.name))
            self.encryption_type_cb.setDisabled(True)

        # Show Window
        self.window.exec_()
