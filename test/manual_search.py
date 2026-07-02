import chromadb
from sentence_transformers import SentenceTransformer
from query_router import route_query

DB_PATH = "./my_vectordb"
COLLECTION_NAME = "insurance_docs"
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

model = SentenceTransformer(EMBEDDING_MODEL)
client = chromadb.PersistentClient(path=DB_PATH)
collection = client.get_collection(COLLECTION_NAME)


def search_with_routing(query: str, n_results: int = 3):
    # ขั้นที่ 1: ให้ Router จำแนกหมวดหมู่ก่อน
    category = route_query(query)
    print(f"คำถาม: {query}")
    print(f"   🧭 Router จำแนกเป็นหมวด: {category}")

    # ขั้นที่ 2: ตั้ง filter ตามหมวดที่ได้ (ถ้าเป็น general ไม่ filter)
    where_filter = None if category == "general" else {"category": category}

    # ขั้นที่ 3: ค้นหาจริงพร้อม filter
    query_embedding = model.encode([query]).tolist()
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=n_results,
        where=where_filter,
    )

    print(f"   📋 ผลลัพธ์การค้นหา (filter: {where_filter}):")
    for i, (doc_id, metadata) in enumerate(zip(
        results["ids"][0], results["metadatas"][0]
    )):
        print(f"      {i+1}. {doc_id} (category: {metadata['category']})")
    print()


if __name__ == "__main__":
    # คำถามเดิมที่เคยมีปัญหา LIFE-001 ปนมา
    search_with_routing("เมาแล้วขับเคลมประกันได้ไหม")
    search_with_routing("กู้เงินจากกรมธรรม์ได้เท่าไหร่")