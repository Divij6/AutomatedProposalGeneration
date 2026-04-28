"""
chunk_model.py

Defines the Chunk model produced by Phase 2 (chunking).

A Chunk represents a small, context-aware piece of a document
ready to be embedded and stored in the vector database.

Each chunk contains:
    - chunk_id
    - text
    - metadata
"""

from pydantic import BaseModel, Field
from typing import Dict


class Chunk(BaseModel):
    chunk_id: str = Field(
        description="Unique chunk ID e.g. 'c_0001'"
    )

    text: str = Field(
        description="The chunk text that will be embedded."
    )
    is_table: bool = Field( 
        default=False,
        description="True if this chunk is a table."
    )

    language: str = Field(
        default="en",
        description="ISO language code e.g. 'en', 'hi'"
    )
    metadata: Dict = Field(
        default_factory=dict,
        description="Metadata used for filtering during retrieval."
    )