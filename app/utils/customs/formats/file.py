from config.settings import AWS_SETTINGS, APP_SETTINGS
from .base import BaseFormat


class FileFormat(str, BaseFormat):
    base_url = f'{AWS_SETTINGS.CDN_URL}/{APP_SETTINGS.MEDIA_URL}'
    json_schema = {
        "type": "string", "format": "string",
        "description": "URL to the file.", 'example': f'{base_url}/profiles/image.png'
    }

    @classmethod
    def validate(cls, v=None, *args, **kwargs):
        if v and isinstance(v, str):
            return f'{cls.base_url}{v}'
        return "https://img.freepik.com/premium-vector/vector-illustration-young-man-face-with-short-brown-hair-cartoon-male-character_87771-31254.jpg"


class HrCoreFileFormat(FileFormat):
    base_url = f'{AWS_SETTINGS.HR_CDN_URL}/{APP_SETTINGS.MEDIA_URL}'

    @classmethod
    def validate(cls, v=None, *args, **kwargs):
        if v and isinstance(v, str):
            return f'{cls.base_url}{v}'
        return "https://img.freepik.com/premium-vector/vector-illustration-young-man-face-with-short-brown-hair-cartoon-male-character_87771-31254.jpg"
