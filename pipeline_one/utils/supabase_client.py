import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

import uuid


def upload_file_to_supabase(
        file,
        bucket_name,
        folder_name
):

    file_ext = file.filename.split(".")[-1]

    unique_name = (
        f"{uuid.uuid4()}.{file_ext}"
    )

    file_path = (
        f"{folder_name}/{unique_name}"
    )

    file_bytes = file.file.read()

    response = supabase.storage.from_(
        bucket_name
    ).upload(

        path=file_path,

        file=file_bytes

    )

    return file_path