# This Python file uses the following encoding: utf-8
import os
import shutil
import time
from datetime import datetime

from PySide2 import QtWidgets
from PySide2.QtCore import *
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import QDialog

from helper import ChecksumType, EncryptionType, chacha20poly1305_decrypt_data, \
    decompress_bytes_to_string_b64zlib, get_checksum_sha256, sizeof_fmt
from settings import settings


class RestoreBackupDialog(QObject):
    def __init__(self, db_code: str, ui_path, no_gui=False, password: str = "", *args, **kwargs):
        super(RestoreBackupDialog, self).__init__(*args, **kwargs)
        # Load the .ui file
        ui_file = QFile(ui_path)
        ui_file.open(QFile.ReadOnly)
        loader = QUiLoader()
        self.window = loader.load(ui_file)

        self.db_code = db_code

        # Find widgets
        self.password_le = self.window.findChild(QtWidgets.QLineEdit, 'password_le')
        self.log_pte = self.window.findChild(QtWidgets.QPlainTextEdit, 'log_pte')
        self.restore_pb = self.window.findChild(QtWidgets.QPushButton, 'restore_pb')
        self.cancel_pb = self.window.findChild(QtWidgets.QPushButton, 'cancel_pb')
        self.restore_pb.clicked.connect(self.restore_pb_clicked)
        self.cancel_pb.clicked.connect(self.cancel_pb_clicked)

        if len(password) > 0:  # set password
            self.password_le.setText(password)

        if not no_gui:  # Do not show window
            # Show Window
            self.window.exec_()


    def log_info(self, txt: str, color=None):
        if color:
            self.log_pte.appendHtml('<p style="color: {};">{}</p>'.format(color, txt))
        else:
            self.log_pte.appendHtml('<p>{}</p>'.format(txt))
        self.log_pte.repaint()


    def cancel_pb_clicked(self):
        self.window.done(QDialog.DialogCode.Rejected)


    def restore_pb_clicked(self):
        is_error = False
        try:
            secret_b = self.password_le.text().encode()
            bd_data = decompress_bytes_to_string_b64zlib(self.db_code)
            # print(len(bd_data))
            # print(bd_data)
            key = bd_data[:32]
            # print(key)
            nonce = bd_data[32:44]
            # print(nonce)
            encrypted_data = bd_data[44:]
            self.log_info("Decrypting code...")
            raw_db_backup_data = chacha20poly1305_decrypt_data(data=encrypted_data,
                                                               secret=secret_b,
                                                               key=key, nonce=nonce)
            self.log_info("Done", color="green")
            db_code_chunks = raw_db_backup_data.decode().split('^')
            self.log_info("Found {} chunks".format(len(db_code_chunks)))

            db_c_raw_parts = []
            db_c_i = 0
            # Prepare new db file path
            new_db_filepath = os.path.join(settings.config['general']['tempdir'],
                                           "wbh_{}.db".format(datetime.today().strftime('%Y%m%d%H%M%S')))
            # Open db file to write on
            with open(new_db_filepath, 'wb') as new_db_f:
                for db_c in db_code_chunks:
                    # Extract chunk data from string
                    self.log_info("Extracting data from chunk {} ...".format(db_c_i))
                    db_c_parts = db_c.split(';')
                    encryption_type: EncryptionType = EncryptionType[db_c_parts[0]]
                    encryption_data = db_c_parts[1]
                    checksum_type: ChecksumType = ChecksumType[db_c_parts[2]]
                    checksum = db_c_parts[3]
                    file_id = db_c_parts[4]
                    self.log_info("Done", color="green")

                    self.log_info("Chunk {} encrypted with {}".format(db_c_i, encryption_type.name))
                    if encryption_type == EncryptionType.ChaCha20Poly1305:
                        # Extract key and nonce for decryption
                        dc_c_key_hex, db_c_nonce_hex = encryption_data.split('O')
                        # Prepare chunk file path
                        db_c_filepath = os.path.join(settings.config['general']['tempdir'], "chunk_{}".format(db_c_i))
                        # Download chunk file
                        self.log_info("Downloading chunk {} ...".format(db_c_i))
                        db_c_file = settings.TelegramBot.get_file_by_id(file_id=file_id,
                                                                        path_to_save=db_c_filepath)
                        if db_c_file:  # if file downloaded
                            self.log_info("Done", color="green")
                            with open(db_c_filepath, 'rb') as db_c_f:
                                # Read whole chunk
                                db_c_data = db_c_f.read()
                                self.log_info("Chunk {} is {}".format(db_c_i, sizeof_fmt(len(db_c_data))))
                                # Decrypt data
                                self.log_info("Decrypting chunk {} ...".format(db_c_i))
                                db_c_raw = chacha20poly1305_decrypt_data(data=db_c_data, secret=secret_b,
                                                                         key=bytes.fromhex(dc_c_key_hex),
                                                                         nonce=bytes.fromhex(db_c_nonce_hex))
                                self.log_info("Done", color="green")
                                if checksum_type == ChecksumType.SHA256:
                                    db_c_raw_checksum = get_checksum_sha256(db_c_raw)
                                    if db_c_raw_checksum == checksum:  # compare checksum
                                        new_db_f.write(db_c_raw)
                                        self.log_info("Chunk {} decrypted successfully.".format(db_c_i))
                                    else:
                                        # Mismatch checksum
                                        self.log_info("Error! Mismatch checksum. "
                                                      "check database code and password again.", "red")
                                        is_error = True
                                        break
                                else:
                                    # Unsupported checksum
                                    self.log_info("Error! ChecksumType is not supported.", "red")
                                    is_error = True
                                    break
                        else:
                            # Fail to get file
                            self.log_info("Failed", color="red")
                            self.log_info("Error! Could not download chunk file.", "red")
                            is_error = True
                            break
                    else:
                        # Unsupported Encryption
                        self.log_info("Error! EncryptionType is not supported.", "red")
                        is_error = True
                        break
                    db_c_i += 1
            # check if there was any error
            if not is_error:
                self.log_info("New database downloaded completely.")
                # Backup last db
                for bi in reversed(range(1, settings.config['keep_db_backup'] + 1)):
                    backup_to = "{}.backup-{}".format(settings.config['general']['db_filepath'], bi)
                    # Remove oldest backup if exist
                    if bi == settings.config['general']['keep_db_backup']:
                        if os.path.exists(backup_to):
                            os.remove(backup_to)
                    if bi > 1:  # On newest backup
                        backup_from = "{}.backup-{}".format(settings.config['general']['db_filepath'], bi - 1)
                    else:
                        backup_from = settings.config['general']['db_filepath']
                    # move backup if exit
                    if os.path.exists(backup_from):
                        shutil.move(backup_from, backup_to)
                # Replace downloaded db with current client db
                shutil.move(new_db_filepath, settings.config['general']['db_filepath'])
                time.sleep(1)
                self.window.done(QDialog.DialogCode.Accepted)
                return True
            else:
                self.log_info("Failed to restore db file completely.", "red")

        except Exception as e:
            self.log_info("Error! Can not restore. check database code and password again.\n{}".format(str(e)), "red")
        return False
