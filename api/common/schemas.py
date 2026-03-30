from pydantic import BaseModel
from fastapi import UploadFile

from utils.customs import as_form


@as_form
class UpdateFileSchema(BaseModel):
    file_id: int
    file: UploadFile