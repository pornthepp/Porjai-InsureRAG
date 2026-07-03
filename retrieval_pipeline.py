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
# เอกสารอันดับ 1 ที่ระยะห่าง embedding ใกล้ระดับนี้ถือว่า "มั่นใจสูง" ว่าเกี่ยวข้องจริง
# ให้เชื่อระยะห่างเป็นหลักแทนที่จะพึ่ง AI grader อย่างเดียว เพราะพิสูจน์แล้วว่า grader
# (โมเดลเล็ก) ตัดสินไม่เสถียร คำถามความหมายเดียวกันแต่เรียงประโยคต่างกันเล็กน้อยให้ผล
# ต่างกันได้ ในขณะที่ระยะห่าง embedding นิ่งและแม่นกว่าเวลามั่นใจสูงขนาดนี้
HIGH_CONFIDENCE_DISTANCE_THRESHOLD = 0.25

# โหลดโมเดลและ client ครั้งเดียวตอน import
_model = SentenceTransformer(EMBEDDING_MODEL)
_client = chromadb.PersistentClient(path=DB_PATH)
_collection = _client.get_collection(COLLECTION_NAME)


def _query_collection(query_embedding, n_results, where_filter):
    """query ผ่าน _collection ที่แคชไว้ ถ้า collection ถูกลบ+สร้างใหม่จากภายนอก
    (เช่น มีคนรัน ingest.py ใหม่ระหว่างที่ backend process นี้ยังรันอยู่) ChromaDB จะ
    โยน error "Collection [uuid] does not exist" เพราะ reference เก่าอ้างถึง uuid
    ที่ไม่มีอยู่แล้ว ในกรณีนี้ให้ขอ reference ใหม่จาก _client แล้ว query ซ้ำอีกครั้งเดียว
    แทนที่จะต้อง restart process ทุกครั้งที่มีคนรัน ingest.py ใหม่
    """
    global _collection
    try:
        return _collection.query(
            query_embeddings=query_embedding,
            n_results=n_results,
            where=where_filter,
        )
    except Exception as exc:
        if "does not exist" not in str(exc):
            raise
        _collection = _client.get_collection(COLLECTION_NAME)
        return _collection.query(
            query_embeddings=query_embedding,
            n_results=n_results,
            where=where_filter,
        )


def _search_and_grade(question: str, category: str, n_results: int = 3) -> list[dict]:
    """ค้นหา ChromaDB ด้วย filter ตามหมวด แล้วค่อยส่งต่อให้ grader เฉพาะเอกสารที่ใกล้พอ"""
    where_filter = None if category == "general" else {"category": category}

    query_embedding = _model.encode([question]).tolist()
    results = _query_collection(query_embedding, n_results, where_filter)

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

    graded_docs = grade_documents(question, retrieved_docs)

    if distances and distances[0] <= HIGH_CONFIDENCE_DISTANCE_THRESHOLD:
        top_id = ids[0]
        if not any(doc["id"] == top_id for doc in graded_docs):
            top_doc = next(doc for doc in retrieved_docs if doc["id"] == top_id)
            graded_docs = [top_doc] + graded_docs

    return graded_docs