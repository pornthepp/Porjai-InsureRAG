from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer
from retrieval_grader import grade_documents

# ผูก DB_PATH กับตำแหน่งไฟล์นี้ (project root) แทน cwd ตอนรัน
# กัน ChromaDB โหลด collection พังถ้า backend/entrypoint อื่นถูกรันจาก dir อื่น
_PROJECT_ROOT = Path(__file__).resolve().parent
DB_PATH = str(_PROJECT_ROOT / "my_vectordb")
COLLECTION_NAME = "insurance_docs"
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
MAX_GRADE_DISTANCE_THRESHOLD = 0.5
MAX_DISTANCE_THRESHOLD = 0.5

# โหลดโมเดลและ client ครั้งเดียวตอน import
_model = SentenceTransformer(EMBEDDING_MODEL)
_client = chromadb.PersistentClient(path=DB_PATH)
_collection = _client.get_collection(COLLECTION_NAME)


def _search_and_grade(question: str, category: str, n_results: int = 3) -> list[dict]:
    """ค้นหา ChromaDB ด้วย filter ตามหมวด แล้วค่อยส่งต่อให้ grader เฉพาะเอกสารที่ใกล้พอ"""
    where_filter = None if category == "general" else {"category": category}

    query_embedding = _model.encode([question]).tolist()
    results = _collection.query(
        query_embeddings=query_embedding,
        n_results=n_results,
        where=where_filter,
    )

    ids = results["ids"][0]
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results.get("distances", [[]])[0]

    if not ids:
        return []

    if distances and min(distances) > MAX_DISTANCE_THRESHOLD:
        return []

    retrieved_docs = []

    if distances:
        for doc_id, text, metadata, distance in zip(
            ids,
            documents,
            metadatas,
            distances,
        ):
            if distance <= MAX_GRADE_DISTANCE_THRESHOLD:
                retrieved_docs.append(
                    {
                        "id": doc_id,
                        "text": text,
                        "metadata": metadata,
                    }
                )
    else:
        retrieved_docs = [
            {"id": doc_id, "text": text, "metadata": metadata}
            for doc_id, text, metadata in zip(
                ids,
                documents,
                metadatas,
            )
        ]

    if not retrieved_docs:
        return []

    return grade_documents(question, retrieved_docs)