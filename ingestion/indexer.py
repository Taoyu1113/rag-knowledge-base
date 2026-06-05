# -*- coding: utf-8 -*-
import uuid
import os

import chromadb

from ingestion.embedder import get_embedding
from config import CHROMA_PATH, COLLECTION_NAME

client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"},
)


def index_chunks(chunks, course="默认", source="unknown", chunk_metas=None):
    """
    将 chunk 列表向量化并存入 ChromaDB。

    参数：
      chunks:      字符串列表（兼容旧接口）或 dict 列表 [{"text":"...", "page":1, "section":"..."}, ...]
      course:      课程名称
      source:      来源文件名
      chunk_metas: 额外的 metadata 列表（当 chunks 为纯文本时使用）
    """
    for i, chunk in enumerate(chunks):
        # 兼容两种输入格式：纯文本 或 带元数据的 dict
        if isinstance(chunk, dict):
            text = chunk.get("text", "")
            page = chunk.get("page", 0)
            section = chunk.get("section", "")
        else:
            text = chunk
            page = 0
            section = ""

        # 如果传入了 chunk_metas，合并进来
        if chunk_metas and i < len(chunk_metas):
            meta = chunk_metas[i]
            if isinstance(meta, dict):
                page = meta.get("page", page)
                section = meta.get("section", section)

        embedding = get_embedding(text)
        chunk_id = str(uuid.uuid4())

        metadata = {
            "course": course,
            "source": os.path.basename(source),
            "chunk_index": i,
            "page": page,
            "section": section,
        }

        collection.add(
            documents=[text],
            embeddings=[embedding],
            metadatas=[metadata],
            ids=[chunk_id],
        )
    print(f"入库完成: {len(chunks)} chunks")


def list_courses():
    result = collection.get(include=["metadatas"])
    courses = set()
    for meta in result["metadatas"]:
        if "course" in meta:
            courses.add(meta["course"])
    return sorted(courses)


def get_course_stats():
    result = collection.get(include=["metadatas"])
    stats = {}
    for meta in result["metadatas"]:
        course = meta.get("course", "默认")
        stats[course] = stats.get(course, 0) + 1
    return stats


def delete_course(course):
    collection.delete(where={"course": course})


def list_sources(course):
    result = collection.get(where={"course": course}, include=["metadatas"])
    sources = set()
    for meta in result["metadatas"]:
        if "source" in meta:
            sources.add(meta["source"])
    return sorted(sources)


def get_source_count(course, source):
    result = collection.get(
        where={"$and": [{"course": course}, {"source": source}]},
        include=["metadatas"],
    )
    return len(result["ids"])


def delete_source(course, source):
    collection.delete(
        where={"$and": [{"course": course}, {"source": source}]}
    )
