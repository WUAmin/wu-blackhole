#!/usr/bin/python3
# -*- coding: utf-8 -*-
import uuid
from enum import Enum


class QueueState(Enum):
    NEW = 10  # Just discovered
    CHANGED = 20  # Size is changing (root level item)
    UNCHANGED = 30  # Size did not change during the interval (root level item)
    INQUEUE = 40  # Item moved to queue and waiting in queue for upload
    UPLOADING = 50  # Uploading and adding item itself to database (Not recursive)
    DONE = 60  # Item added to database and uploaded (Not recursive)
    DELETED = 70  # Item is deleted from disk not queue


class ChecksumType(Enum):
    NONE = 0
    MD5 = 10
    SHA1 = 20
    SHA256 = 30
    SHA512 = 40


class EncryptionType(Enum):
    NONE = 0
    ChaCha20Poly1305 = 10
    FERNET_SHA256 = 20
    AES_SHA256 = 30


class WBHChunk:
    def __init__(self, size, filename, index=-1, org_filename=None, org_fullpath=None, org_size=None,
                 msg_id=None, state: QueueState = QueueState.INQUEUE, checksum: str = None,
                 checksum_type: ChecksumType = None, encryption: EncryptionType = EncryptionType.NONE,
                 encryption_data: str = None, parent_qid: int = None, parent_db_id=None, db_id=None):
        self.size = size
        self.index = index
        self.filename = filename
        self.org_filename = org_filename
        self.org_fullpath = org_fullpath
        self.org_size = org_size
        self.msg_id = msg_id
        self.state: QueueState = state
        self.checksum: str = checksum
        self.checksum_type: ChecksumType = checksum_type
        self.encryption: EncryptionType = encryption
        self.encryption_data: str = encryption_data
        self.parent_qid: int = parent_qid
        self.parent_db_id = parent_db_id
        self.db_id = db_id


    def to_dict(self):
        return {'size': self.size,
                'index': self.index,
                'filename': self.filename,
                'org_filename': self.org_filename,
                'org_fullpath': self.org_fullpath,
                'org_size': self.org_size,
                'msg_id': self.msg_id,
                'state': self.state.name,
                'checksum': self.checksum,
                'checksum_type': self.checksum_type.name,
                'encryption': self.encryption.name,
                'encryption_data': self.encryption_data,
                'parent_qid': self.parent_qid,
                'parent_db_id': self.parent_db_id,
                'db_id': self.db_id}


    @staticmethod
    def from_dict(_dict):
        return WBHChunk(size=_dict['size'],
                        index=_dict['index'],
                        filename=_dict['filename'],
                        org_filename=_dict['org_filename'],
                        org_fullpath=_dict['org_fullpath'],
                        org_size=_dict['org_size'],
                        msg_id=_dict['msg_id'],
                        state=QueueState[_dict['state']],
                        checksum=_dict['checksum'],
                        checksum_type=ChecksumType[_dict['checksum_type']],
                        encryption=EncryptionType[_dict['encryption']],
                        encryption_data=_dict['encryption_data'],
                        parent_qid=_dict['parent_qid'],
                        parent_db_id=_dict['parent_db_id'],
                        db_id=_dict['db_id'])


class WBHItem:
    def __init__(self, filename: str, full_path: str = None, root_path: str = None, is_dir: bool = False,
                 size: int = -1, state: QueueState = QueueState.NEW, parents: list = None, parent_qid=None,
                 children: list = None, qid=None, db_id=None, chunks: list = None, total: int = -1,
                 modified_at=None, created_at=None, checksum: str = None,
                 checksum_type: ChecksumType = ChecksumType.NONE):
        if parents is None:
            parents = list()
        if qid is None:
            qid = uuid.uuid4().int
        self.filename = filename
        self.full_path = full_path
        self.root_path = root_path
        self.is_dir = is_dir
        self.size = size
        self.state = state
        self.parents: list = parents
        self.parent_qid: int = parent_qid
        self.children: list = children
        self.qid = qid
        self.db_id = db_id
        self.chunks: list = chunks
        self.total_children: int = total
        self.modified_at = modified_at
        self.created_at = created_at
        self.checksum: str = checksum
        self.checksum_type: ChecksumType = checksum_type


    def to_dict(self):
        children = None
        if self.children is not None:
            children = [child.to_dict() for child in self.children]
        chunks = None
        if self.chunks is not None:
            chunks = [ch.to_dict() for ch in self.chunks]

        return {'qid': self.qid,
                'db_id': self.db_id,
                'size': self.size,
                'full_path': self.full_path,
                'root_path': self.root_path,
                'filename': self.filename,
                'is_dir': self.is_dir,
                'state': self.state.name,
                'parents': self.parents,
                'parent_qid': self.parent_qid,
                'children': children,
                'chunks': chunks,
                'total_children': self.total_children,
                'modified_at': self.modified_at,
                'created_at': self.created_at,
                'checksum': self.checksum,
                'checksum_type': self.checksum_type.name}


    @staticmethod
    def from_dict(_dict):
        children = None
        if _dict['children'] is not None:
            children = [WBHItem.from_dict(child) for child in _dict['children']]
        chunks = None
        if _dict['chunks'] is not None:
            chunks = [WBHChunk.from_dict(ch) for ch in _dict['chunks']]

        return WBHItem(qid=_dict['qid'],
                       db_id=_dict['db_id'],
                       size=_dict['size'],
                       full_path=_dict['full_path'],
                       root_path=_dict['root_path'],
                       filename=_dict['filename'],
                       is_dir=_dict['is_dir'],
                       state=QueueState[_dict['state']],
                       parents=_dict['parents'],
                       parent_qid=_dict['parent_qid'],
                       children=children,
                       chunks=chunks,
                       total=_dict['total_children'],
                       modified_at=_dict['modified_at'],
                       created_at=_dict['created_at'],
                       checksum=_dict['checksum'],
                       checksum_type=ChecksumType[_dict['checksum_type']])
