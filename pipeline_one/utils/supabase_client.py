import os
import uuid
from pathlib import Path

from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def upload_file_to_supabase(
        file,
        bucket_name,
        folder_name
):
    if isinstance(file, (str, Path)):
        source_path = Path(file)
        file_ext = source_path.suffix.lstrip(".") or "bin"
        file_bytes = source_path.read_bytes()
    else:
        file_ext = file.filename.split(".")[-1]
        file_bytes = file.file.read()

    unique_name = f"{uuid.uuid4()}.{file_ext}"

    file_path = f"{folder_name}/{unique_name}"

    supabase.storage.from_(bucket_name).upload(

        path=file_path,

        file=file_bytes

    )

    return file_path
