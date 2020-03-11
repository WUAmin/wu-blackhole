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
        self.ID = _id
        self.Size = size
        self.RootPath = root_path
        self.FullPath = full_path
        self.Filename = filename
        self.IsDir = is_dir
        self.State = state
        self.Parents: list = parents
        self.Children: list = children
        self.Chunks: list = chunks
        self.TotalChildren: int = total
        self.ModifiedAt = modified_at
        self.CreatedAt = created_at


    def to_dict(self):
        children = None
        if self.Children is not None:
            children = [child.to_dict() for child in self.Children]
        chunks = None
        if self.Chunks is not None:
            chunks = [ch.to_dict() for ch in self.Chunks]

        return {'ID': self.ID,
                'Size': self.Size,
                'FullPath': self.FullPath,
                'RootPath': self.RootPath,
                'Filename': self.Filename,
                'IsDir': self.IsDir,
                'State': self.State.value,
                'Parents': self.Parents,
                'Children': children,
                'Chunks': chunks,
                'TotalChildren': self.TotalChildren,
                'ModifiedAt': self.ModifiedAt,
                'CreatedAt': self.CreatedAt}


    @staticmethod
    def from_dict(_dict):
        children = None
        if _dict['Children'] is not None:
            children = [WBHItem.from_dict(child) for child in _dict['Children']]
        chunks = None
        if _dict['Chunks'] is not None:
            chunks = [WBHChunk.from_dict(ch) for ch in _dict['Chunks']]

        return WBHItem(_id=_dict['ID'],
                       full_path=_dict['FullPath'],
                       filename=_dict['Filename'],
                       root_path=_dict['RootPath'],
                       is_dir=_dict['IsDir'],
                       size=_dict['Size'],
                       state=WBHItemState(_dict['State']),
                       parents=_dict['Parents'],
                       children=children,
                       chunks=chunks,
                       total=_dict['TotalChildren'],
                       modified_at=_dict['ModifiedAt'],
                       created_at=_dict['CreatedAt'])
