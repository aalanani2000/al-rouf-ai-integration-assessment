"""
Document loading and chunking for the bilingual RAG pipeline.

Documents are kept as simple Markdown files under documents/, loaded
and split into overlapping chunks at section/paragraph boundaries.
This is intentionally simple — no PDF parsing or external loaders —
since the brief asks for a workflow over 3-5 sample documents, not a
general-purpose document ingestion system.
"""

import os
import re
from dataclasses import dataclass

DOCUMENTS_DIR = os.path.join(os.path.dirname(__file__), "..", "documents")


@dataclass
class Chunk:
    chunk_id: str
    source_doc: str
    text: str


def load_documents(directory: str = None) -> dict[str, str]:
    """Load all .md files in the documents directory. Returns {filename: content}."""
    directory = directory or DOCUMENTS_DIR
    docs = {}
    for filename in sorted(os.listdir(directory)):
        if filename.endswith(".md"):
            path = os.path.join(directory, filename)
            with open(path, "r", encoding="utf-8") as f:
                docs[filename] = f.read()
    return docs


def chunk_document(filename: str, content: str, max_chunk_chars: int = 800) -> list[Chunk]:
    """
    Split a document into chunks along '## ' section headers first
    (since our sample docs are structured this way), falling back to
    paragraph splitting if a section is still too long.
    """
    sections = re.split(r"\n(?=## )", content)
    chunks = []
    chunk_index = 0

    for section in sections:
        section = section.strip()
        if not section:
            continue

        if len(section) <= max_chunk_chars:
            chunks.append(
                Chunk(
                    chunk_id=f"{filename}::chunk{chunk_index}",
                    source_doc=filename,
                    text=section,
                )
            )
            chunk_index += 1
        else:
            # Section too long — split further on paragraph breaks
            paragraphs = section.split("\n\n")
            buffer = ""
            for para in paragraphs:
                # A single paragraph can itself exceed max_chunk_chars (e.g. one
                # long unbroken line of text with no \n\n inside it). Hard-split
                # it on whitespace boundaries so we never emit an oversized chunk.
                if len(para) > max_chunk_chars:
                    words = para.split(" ")
                    sub_buffer = ""
                    for word in words:
                        if len(sub_buffer) + len(word) + 1 <= max_chunk_chars:
                            sub_buffer += (" " if sub_buffer else "") + word
                        else:
                            if buffer:
                                chunks.append(
                                    Chunk(
                                        chunk_id=f"{filename}::chunk{chunk_index}",
                                        source_doc=filename,
                                        text=buffer,
                                    )
                                )
                                chunk_index += 1
                                buffer = ""
                            chunks.append(
                                Chunk(
                                    chunk_id=f"{filename}::chunk{chunk_index}",
                                    source_doc=filename,
                                    text=sub_buffer,
                                )
                            )
                            chunk_index += 1
                            sub_buffer = word
                    if sub_buffer:
                        buffer = sub_buffer
                    continue

                if len(buffer) + len(para) <= max_chunk_chars:
                    buffer += ("\n\n" if buffer else "") + para
                else:
                    if buffer:
                        chunks.append(
                            Chunk(
                                chunk_id=f"{filename}::chunk{chunk_index}",
                                source_doc=filename,
                                text=buffer,
                            )
                        )
                        chunk_index += 1
                    buffer = para
            if buffer:
                chunks.append(
                    Chunk(
                        chunk_id=f"{filename}::chunk{chunk_index}",
                        source_doc=filename,
                        text=buffer,
                    )
                )
                chunk_index += 1

    return chunks


def load_and_chunk_all(directory: str = None) -> list[Chunk]:
    """Load every document and return a flat list of all chunks across all docs."""
    docs = load_documents(directory)
    all_chunks = []
    for filename, content in docs.items():
        all_chunks.extend(chunk_document(filename, content))
    return all_chunks
