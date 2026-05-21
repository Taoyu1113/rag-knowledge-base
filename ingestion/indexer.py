import chromadb
from chromadb.config import Settings

from ingestion.embedder import get_embedding


client = chromadb.Client(Settings(
    persist_directory="database/chroma_store"
))

collection = client.get_or_create_collection(name="rag_db")

#！！！把每个 chunk 变成向量，存进数据库
def index_chunks(chunks):
    for i, chunk in enumerate(chunks):
        embedding = get_embedding(chunk)

        collection.add(
            documents=[chunk],
            embeddings=[embedding],
            ids=[str(i)]
        )

    client.persist()