import chromadb
from ingestion.embedder import get_embedding

client = chromadb.PersistentClient(
    path="database/chroma_store"
)

collection = client.get_or_create_collection(name="rag_db")


def search(query, top_k=3):
    query_embedding = get_embedding(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )

    return results["documents"][0]


if __name__ == "__main__":
    print("start search...")

    res = search("抗战精神是什么")

    print("search done")

    for i, r in enumerate(res):
        print(f"\n--- result {i} ---\n")
        print(r)
    print(collection.count())