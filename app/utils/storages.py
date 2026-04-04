import logging
import mimetypes
import os
from dataclasses import dataclass, field
from functools import cached_property
from io import BytesIO

import aioboto3
import aiofiles
import aiohttp
import botocore
from botocore.config import Config
from botocore.exceptions import ClientError
from fastapi import UploadFile

from config.settings import AWS_SETTINGS

EXT_TO_MIME = {
    '.doc': 'application/msword',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.ppt': 'application/vnd.ms-powerpoint',
    '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    '.xls': 'application/vnd.ms-excel',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.pdf': 'application/pdf',
    '.txt': 'text/plain',
    '.csv': 'text/csv',
    '.zip': 'application/zip',
    '.rar': 'application/vnd.rar',
    '.7z': 'application/x-7z-compressed',
    '.tar': 'application/x-tar',
    '.gz': 'application/gzip',

    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.bmp': 'image/bmp',
    '.webp': 'image/webp',
    '.svg': 'image/svg+xml',
    '.tif': 'image/tiff',
    '.tiff': 'image/tiff',
    '.ico': 'image/x-icon',
    '.heic': 'image/heic',
    '.heif': 'image/heif',

    '.mp4': 'video/mp4',
    '.mov': 'video/quicktime',
    '.avi': 'video/x-msvideo',
    '.mkv': 'video/x-matroska',
    '.webm': 'video/webm',
    '.flv': 'video/x-flv',
    '.wmv': 'video/x-ms-wmv',
    '.3gp': 'video/3gpp',

    '.mp3': 'audio/mpeg',
    '.wav': 'audio/wav',
    '.ogg': 'audio/ogg',
    '.aac': 'audio/aac',
    '.flac': 'audio/flac',
    '.m4a': 'audio/mp4',
    '.opus': 'audio/opus',
    '.weba': 'audio/webm',
}


def get_content_type(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    res = EXT_TO_MIME.get(ext, mimetypes.guess_type(filename)[0] or 'application/octet-stream')
    return res


@dataclass
class Storage:
    aws_access_key_id: str
    aws_secret_access_key: str
    region_name: str
    bucket: str
    media_folder: str
    chunk_size = 1024
    base_url: str = field(default=AWS_SETTINGS.AWS_ENDPOINT_URL)

    def __post_init__(self):
        self.config = Config(
            region_name="auto",
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        )

    @cached_property
    def aioboto3_session(self):
        return aioboto3.Session(
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.region_name,
        )

    @cached_property
    def aiohttp_session(self):
        return aiohttp.ClientSession()

    @property
    def new_aiohttp_session(self):
        return aiohttp.ClientSession()

    async def async_upload_file(self, file_path: str, s3_file_name: str):
        s3_key = self.media_folder + s3_file_name
        async with self.aioboto3_session.client('s3', config=self.config, endpoint_url=self.base_url) as s3:
            await s3.upload_file(
                file_path,
                self.bucket,
                s3_key,
                ExtraArgs={'ContentType': get_content_type(s3_key)}
            )

    async def upload_aws_from_url(self, url: str, s3_key: str):
        s3_key = self.media_folder + s3_key

        async with self.aiohttp_session.get(url) as resp:
            if resp.status != 200:
                raise Exception(f"Failed to fetch URL: {resp.status}")

            file_data = await resp.read()

        async with self.aioboto3_session.client(
                "s3",
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.region_name,
                config=self.config,
                endpoint_url=self.base_url,
        ) as s3:
            await s3.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=file_data
            )

        return

    async def async_upload_fileobj(self, file: BytesIO, filename: str = None):
        filename = self.media_folder + filename
        file.seek(0)
        async with self.aioboto3_session.client("s3", config=self.config, endpoint_url=self.base_url) as s3:
            await s3.upload_fileobj(
                file,
                AWS_SETTINGS.AWS_BUCKET_NAME,
                filename,
                ExtraArgs={'ContentType': get_content_type(filename)}
            )
        return filename

    async def async_download_file(self, s3_file_name: str, local_path: str):
        async with self.aioboto3_session.client('s3', config=self.config) as s3:
            await s3.download_file(AWS_SETTINGS.AWS_BUCKET_NAME, s3_file_name, local_path)

    async def s3_file_exists(self, key: str) -> bool:
        async with self.aioboto3_session.client("s3", config=self.config) as s3:
            try:
                await s3.head_object(Bucket=AWS_SETTINGS.AWS_BUCKET_NAME, Key=key)
                return True
            except botocore.exceptions.ClientError as e:
                if e.response['Error']['Code'] == "404":
                    return False
                raise

    async def async_delete_file(self, s3_file_name: str) -> bool:
        s3_file_name = self.media_folder + s3_file_name
        async with self.aioboto3_session.client("s3", config=self.config, endpoint_url=self.base_url) as s3:
            try:
                await s3.delete_object(Bucket=AWS_SETTINGS.AWS_BUCKET_NAME, Key=s3_file_name)
                return True
            except ClientError as e:
                logging.error(f"Failed to delete file {s3_file_name} from S3: {e}")
                return False

    async def async_upload_uploadfile_to_s3(self, upload_file: UploadFile, s3_file_name: str = None) -> str:
        s3_file_name = s3_file_name or upload_file.filename

        content_type = get_content_type(upload_file.filename)

        async with self.aioboto3_session.client("s3", config=self.config, endpoint_url=self.base_url) as s3:
            await s3.upload_fileobj(
                upload_file.file,
                AWS_SETTINGS.AWS_BUCKET_NAME,
                s3_file_name,
                ExtraArgs={'ContentType': content_type}
            )

        return s3_file_name

    async def delete_file(self, path: str):
        path = self.media_folder + path
        if os.path.exists(path):
            os.remove(path)

    async def save_to_disk(self, file_content: bytes, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        async with aiofiles.open(path, 'wb') as out_file:
            await out_file.write(file_content)

    async def save_to_disk_from_url(self, url: str, path: str):
        path = self.media_folder + path
        os.makedirs(os.path.dirname(path), exist_ok=True)

        if os.path.exists(path):
            return path

        async with self.aiohttp_session.get(url) as resp:
            if resp.status != 200:
                raise Exception(f"Failed to download file: {resp.status} text: {await resp.text()} url: {url}")
            content = await resp.read()
        async with aiofiles.open(path, "wb") as out_file:
            for i in range(0, len(content), self.chunk_size):
                await out_file.write(content[i:i + self.chunk_size])

        return path


storage = Storage(
    aws_access_key_id=AWS_SETTINGS.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SETTINGS.AWS_SECRET_ACCESS_KEY,
    region_name=AWS_SETTINGS.AWS_REGION_NAME,
    bucket=AWS_SETTINGS.AWS_BUCKET_NAME,
    media_folder="media/",
    base_url=AWS_SETTINGS.AWS_ENDPOINT_URL,
)
