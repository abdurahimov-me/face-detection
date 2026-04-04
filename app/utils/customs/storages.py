__all__ = (
    'FileStorageManager',
    'LocalStorageManager',
)

from starlette.datastructures import UploadFile

from utils.customs.formats.file import FileObject
from ..storages import LocalStorageManager


class FileStorageManager(LocalStorageManager):
    file_classes = (UploadFile, FileObject)
