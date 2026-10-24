"""Text extraction and chunking engine with metadata tagging."""

import os
import re
import json
from typing import List, Dict, Any
from pypdf import PdfReader


class ChunkingEngine:
    @staticmethod
    def extract_text_from_file(file_path: str, file_type: str) -> List[Dict[str, Any]]:
        """Extract text segments with source metadata from supported file formats."""
        segments: List[Dict[str, Any]] = []

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        file_type = file_type.lower().strip(".")

        if file_type == "pdf":
            reader = PdfReader(file_path)
            for page_idx, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                if text.strip():
                    segments.append({
                        "text": text.strip(),
                        "metadata": {"page": page_idx + 1, "source_type": "pdf"},
                    })

        elif file_type in ["txt", "md"]:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            if content.strip():
                segments.append({
                    "text": content.strip(),
                    "metadata": {"page": 1, "source_type": file_type},
                })

        elif file_type == "json":
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)

            if isinstance(data, list):
                for idx, item in enumerate(data):
                    q = item.get("question", item.get("q", ""))
                    a = item.get("answer", item.get("a", ""))
                    text = f"Question: {q}\nAnswer: {a}" if q and a else str(item)
                    segments.append({
                        "text": text,
                        "metadata": {"item_index": idx + 1, "source_type": "faq_json"},
                    })
            else:
                segments.append({
                    "text": json.dumps(data, indent=2),
                    "metadata": {"source_type": "json"},
                })
        else:
            # Fallback text reading
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            segments.append({
                "text": content.strip(),
                "metadata": {"source_type": "raw_text"},
            })

        return segments

    @classmethod
    def chunk_document(
        cls,
        file_path: str,
        file_type: str,
        max_chunk_size: int = 800,
        chunk_overlap: int = 100,
    ) -> List[Dict[str, Any]]:
        """Extract text and recursively split into overlapping chunks with structured metadata."""
        segments = cls.extract_text_from_file(file_path, file_type)
        chunks: List[Dict[str, Any]] = []
        chunk_counter = 0

        for seg in segments:
            text = seg["text"]
            seg_meta = seg.get("metadata", {})

            # Clean and normalize whitespace
            normalized_text = re.sub(r"\r\n", "\n", text)
            paragraphs = normalized_text.split("\n\n")

            current_chunk = ""
            current_section = "General"

            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue

                # Check if paragraph is a section header (e.g. # Header or Title:)
                is_header = para.startswith("#") or (len(para) < 60 and para.endswith(":"))
                if is_header and current_chunk:
                    # Flush previous section chunk
                    chunk_counter += 1
                    meta = {**seg_meta, "section": current_section, "char_count": len(current_chunk)}
                    chunks.append({
                        "chunk_index": chunk_counter,
                        "content": current_chunk,
                        "metadata": meta,
                    })
                    current_chunk = ""

                if is_header:
                    current_section = para.strip("# :")

                if len(current_chunk) + len(para) + 2 <= max_chunk_size:
                    current_chunk = f"{current_chunk}\n\n{para}".strip()

                else:
                    if current_chunk:
                        chunk_counter += 1
                        meta = {**seg_meta, "section": current_section, "char_count": len(current_chunk)}
                        chunks.append({
                            "chunk_index": chunk_counter,
                            "content": current_chunk,
                            "metadata": meta,
                        })

                        # Retain overlap from end of previous chunk
                        overlap_text = current_chunk[-chunk_overlap:] if len(current_chunk) > chunk_overlap else ""
                        current_chunk = f"{overlap_text}\n\n{para}".strip()
                    else:
                        # Single paragraph exceeds max_chunk_size, split by sentences
                        sentences = re.split(r"(?<=[.?!])\s+", para)
                        for sentence in sentences:
                            if len(current_chunk) + len(sentence) + 1 <= max_chunk_size:
                                current_chunk = f"{current_chunk} {sentence}".strip()
                            else:
                                if current_chunk:
                                    chunk_counter += 1
                                    meta = {**seg_meta, "section": current_section, "char_count": len(current_chunk)}
                                    chunks.append({
                                        "chunk_index": chunk_counter,
                                        "content": current_chunk,
                                        "metadata": meta,
                                    })
                                current_chunk = sentence

            if current_chunk:
                chunk_counter += 1
                meta = {**seg_meta, "section": current_section, "char_count": len(current_chunk)}
                chunks.append({
                    "chunk_index": chunk_counter,
                    "content": current_chunk,
                    "metadata": meta,
                })

        return chunks
