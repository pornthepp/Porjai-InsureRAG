import os
import re
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

# ผูก path กับตำแหน่งไฟล์นี้ (project root) แทน cwd ตอนรัน ให้ผลเหมือนเดิมไม่ว่ารันจากไหน
_PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = str(_PROJECT_ROOT / "data")
DB_PATH = str(_PROJECT_ROOT / "my_vectordb")
COLLECTION_NAME = "insurance_docs"
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
COLLECTION_METADATA = {"hnsw:space": "cosine"}

def parse_chunks(file_path):
    """อ่านไฟล์ .txt แล้วแบ่งเป็น chunk ตาม metadata header [doc_id]...[last_updated]"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # แบ่งด้วยบรรทัดว่าง 2 บรรทัดขึ้นไป (ระหว่าง chunk)
    raw_blocks = re.split(r"\n\s*\n(?=\[doc_id)", content.strip())

    chunks = []
    for block in raw_blocks:
        block = block.strip()
        if not block:
            continue

        # ดึง metadata ออกจากบรรทัดแรก
        header_match = re.match(
            r"\[doc_id:\s*(.+?)\]\s*\[category:\s*(.+?)\]\s*\[last_updated:\s*(.+?)\]",
            block
        )
        if not header_match:
            print(f"⚠️ ข้าม block ที่ไม่มี metadata header ถูกต้อง: {block[:50]}...")
            continue

        doc_id, category, last_updated = header_match.groups()

        # เนื้อหาที่เหลือหลังตัด header ออก
        text_content = block[header_match.end():].strip()

        chunks.append({
            "id": doc_id.strip(),
            "text": text_content,
            "metadata": {
                "category": category.strip(),
                "last_updated": last_updated.strip(),
                "source_file": os.path.basename(file_path),
            }
        })

    return chunks

def main():
    print("📂 ขั้นที่ 1: อ่านและหั่นไฟล์ข้อมูล...")
    all_chunks = []
    for filename in os.listdir(DATA_DIR):
        if filename.endswith(".txt"):
            file_path = os.path.join(DATA_DIR, filename)
            chunks = parse_chunks(file_path)
            print(f"   - {filename}: ได้ {len(chunks)} chunks")
            all_chunks.extend(chunks)

    print(f"\n✅ รวมทั้งหมด {len(all_chunks)} chunks")

    print("\n🧠 ขั้นที่ 2: โหลด embedding model (อาจใช้เวลาสักครู่ครั้งแรก)...")
    model = SentenceTransformer(EMBEDDING_MODEL)

    print("\n🔢 ขั้นที่ 3: แปลงข้อความเป็น embeddings...")
    texts = [c["text"] for c in all_chunks]
    embeddings = model.encode(texts, show_progress_bar=True).tolist()

    print("\n💾 ขั้นที่ 4: บันทึกลง ChromaDB...")
    client = chromadb.PersistentClient(path=DB_PATH)

    # ลบ collection เก่าถ้ามี (กัน duplicate ตอนรันซ้ำ)
    try:
        client.delete_collection(COLLECTION_NAME)
        print("   - ลบ collection เก่าทิ้งก่อน (รันซ้ำ)")
    except Exception:
        pass

    collection = client.create_collection(
        COLLECTION_NAME,
        metadata=COLLECTION_METADATA,
    )

    collection.add(
        ids=[c["id"] for c in all_chunks],
        embeddings=embeddings,
        documents=texts,
        metadatas=[c["metadata"] for c in all_chunks],
    )

    print(f"\n🎉 เสร็จสิ้น! บันทึก {collection.count()} chunks ลง ChromaDB ที่ {DB_PATH}")


if __name__ == "__main__":
    main()
