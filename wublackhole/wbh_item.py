#!/usr/bin/python3
# -*- coding: utf-8 -*-
import uuid
from enum import Enum


class WBHChunk:
    def __init__(self, size, filename, index=-1, original_filename=None, original_fullpath=None, original_size=None,
                 msg_id=None):
        self.Size = size
        self.Index = index
        self.Filename = filename
        self.OriginalFilename = original_filename
        self.OriginalFullPath = original_fullpath
        self.OriginalSize = original_size
        self.MessageID = msg_id


    def to_dict(self):
        return {'Size': self.Size,
                'Index': self.Index,
                'Filename': self.Filename,
                'OriginalFilename': self.OriginalFilename,
                'OriginalFullPath': self.OriginalFullPath,
                'OriginalSize': self.OriginalSize,
                'MessageID': self.MessageID}


    @staticmethod
    def from_dict(_dict):
        return WBHChunk(size=_dict['Size'],
                        index=_dict['Index'],
                        filename=_dict['Filename'],
                        original_filename=_dict['OriginalFilename'],
                        original_fullpath=_dict['OriginalFullPath'],
                        original_size=_dict['OriginalSize'],
                        msg_id=_dict['MessageID'])


class WBHItemState(Enum):
    NEW = 10
    CHANGED = 20
    UNCHANGED = 30
    INQUEUE = 40
    UPLOADING = 50


class WBHItem:
    def __init__(self, filename: str, full_path: str = None, root_path: str = None, is_dir: bool = False,
                 size: int = -1, state: WBHItemState = WBHItemState.NEW, parents: list = [], children: list = None,
                 _id=uuid.uuid4().int, chunks: list = None, total: int = -1, modified_at=None, created_at=None):
        self.id = _id
        self.size = size
        self.root_path = root_path
        self.full_path = full_path
        self.filename = filename
        self.is_dir = is_dir
        self.state = state
        self.parents: list = parents
        self.children: list = children
        self.chunks: list = chunks
        self.total_children: int = total
        self.modified_at = modified_at
        self.created_at = created_at


    def to_dict(self):
        children = None
        if self.children is not None:
            children = [child.to_dict() for child in self.children]
        chunks = None
        if self.chunks is not None:
            chunks = [ch.to_dict() for ch in self.chunks]

        return {'id': self.id,
                'size': self.size,
                'full_path': self.full_path,
                'root_path': self.root_path,
                'filename': self.filename,
                'is_dir': self.is_dir,
                'state': self.state.value,
                'parents': self.parents,
                'children': children,
                'chunks': chunks,
                'total_children': self.total_children,
                'modified_at': self.modified_at,
                'created_at': self.created_at}


    @staticmethod
    def from_dict(_dict):
        children = None
        if _dict['children'] is not None:
            children = [WBHItem.from_dict(child) for child in _dict['Children']]
        chunks = None
        if _dict['chunks'] is not None:
            chunks = [WBHChunk.from_dict(ch) for ch in _dict['Chunks']]

        return WBHItem(_id=_dict['id'],
                       size=_dict['size'],
                       full_path=_dict['full_path'],
                       root_path=_dict['root_path'],
                       filename=_dict['filename'],
                       is_dir=_dict['is_dir'],
                       state=WBHItemState(_dict['state']),
                       parents=_dict['parents'],
                       children=children,
                       chunks=chunks,
                       total=_dict['total_children'],
                       modified_at=_dict['modified_at'],
                       created_at=_dict['created_at'])
