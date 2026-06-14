"""
ingest.py
---------
Turn a PDF into searchable LangChain Documents.

A PDF can hold three kinds of content, and we handle all three:
  - text   -> extracted directly, split into overlapping chunks
  - tables -> detected per page, turned into Markdown so the LLM can read them
  - images -> sent to GPT-4o vision, which writes a description we can search

Each Document carries metadata (source file, page number, content type) so the
final answer can cite exactly where each fact came from.
"""

import base64
import os
from typing import List

import fitz  # PyMuPDF
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI


def _describe_image(image_bytes: bytes) -> str:
    """Ask GPT-4o vision to describe an image so it becomes searchable text."""
    b64 = base64.b64encode(image_bytes).decode()
    llm = ChatOpenAI(model=os.getenv("VISION_MODEL", "gpt-4o"), temperature=0)
    msg = llm.invoke(
        [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Describe this image from a document in detail. If it is a "
                            "chart or diagram, explain what it shows and any key numbers."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"},
                    },
                ],
            }
        ]
    )
    return msg.content


def load_pdf(path: str, caption_images: bool = True) -> List[Document]:
    """Parse a PDF into Documents (text chunks, tables, image captions)."""
    doc = fitz.open(path)
    source = os.path.basename(path)
    docs: List[Document] = []

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)

    for page_num, page in enumerate(doc, start=1):
        # 1. Text -> overlapping chunks
        text = page.get_text().strip()
        if text:
            for chunk in splitter.split_text(text):
                docs.append(
                    Document(
                        page_content=chunk,
                        metadata={"source": source, "page": page_num, "type": "text"},
                    )
                )

        # 2. Tables -> Markdown (best-effort; not all PDFs have detectable tables)
        try:
            for table in page.find_tables().tables:
                md = table.to_markdown()
                if md and md.strip():
                    docs.append(
                        Document(
                            page_content=f"Table on page {page_num}:\n{md}",
                            metadata={"source": source, "page": page_num, "type": "table"},
                        )
                    )
        except Exception:
            pass

        # 3. Images -> GPT-4o vision captions
        if caption_images:
            for img in page.get_images(full=True):
                xref = img[0]
                try:
                    pix = fitz.Pixmap(doc, xref)
                    if pix.n > 4:  # CMYK -> RGB
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                    if pix.width < 50 or pix.height < 50:
                        continue  # skip tiny icons / bullets / logos
                    caption = _describe_image(pix.tobytes("png"))
                    docs.append(
                        Document(
                            page_content=f"Image on page {page_num}: {caption}",
                            metadata={"source": source, "page": page_num, "type": "image"},
                        )
                    )
                except Exception:
                    continue

    doc.close()
    return docs
