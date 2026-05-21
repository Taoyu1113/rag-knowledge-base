import chromadb

from ingestion.embedder import get_embedding

client = chromadb.PersistentClient(
    path="database/chroma_store"
)

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
    print("入库完成")

