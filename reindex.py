import os
import chromadb
from sentence_transformers import SentenceTransformer
from ingest import (
    parse_chunks,
    DATA_DIR,
    DB_PATH,
    COLLECTION_NAME,
    EMBEDDING_MODEL,
    COLLECTION_METADATA,
)


def get_indexed_files_mtime(collection) -> dict:
    """ดึง mtime ของแต่ละ source_file ที่เคย index ไว้แล้ว (เอาจาก metadata ของ chunk ใดๆ ในไฟล์นั้น)"""
    all_data = collection.get(include=["metadatas"])
    indexed_mtime = {}
    for metadata in all_data["metadatas"]:
        source_file = metadata.get("source_file")
        file_mtime = metadata.get("file_mtime")
        if source_file and file_mtime is not None:
            indexed_mtime[source_file] = file_mtime
    return indexed_mtime


def main():
    print("🔍 ขั้นที่ 1: เช็คไฟล์ที่เปลี่ยนแปลง...")

    client = chromadb.PersistentClient(path=DB_PATH)
    collection = client.get_or_create_collection(
        COLLECTION_NAME,
        metadata=COLLECTION_METADATA,
    )

    indexed_mtime = get_indexed_files_mtime(collection)

    changed_files = []
    for filename in os.listdir(DATA_DIR):
        if not filename.endswith(".txt"):
            continue
        file_path = os.path.join(DATA_DIR, filename)
        current_mtime = os.path.getmtime(file_path)
        previous_mtime = indexed_mtime.get(filename)

        if previous_mtime is None:
            print(f"   🆕 {filename}: ไฟล์ใหม่ ยังไม่เคย index")
            changed_files.append(filename)
        elif current_mtime > previous_mtime:
            print(f"   ♻️ {filename}: แก้ไขใหม่ตั้งแต่ index ครั้งก่อน")
            changed_files.append(filename)
        else:
            print(f"   ✅ {filename}: ไม่เปลี่ยนแปลง ข้าม")

    if not changed_files:
        print("\n🎉 ไม่มีไฟล์ที่ต้อง re-index เลย ฐานข้อมูลล่าสุดอยู่แล้ว")
        return

    print(f"\n🧠 ขั้นที่ 2: โหลด embedding model...")
    model = SentenceTransformer(EMBEDDING_MODEL)

    for filename in changed_files:
        file_path = os.path.join(DATA_DIR, filename)
        current_mtime = os.path.getmtime(file_path)

        print(f"\n📂 กำลัง re-index: {filename}")

        # ลบ chunk เก่าของไฟล์นี้ทิ้งก่อน (กัน duplicate)
        collection.delete(where={"source_file": filename})
        print(f"   🗑️ ลบ chunk เก่าของไฟล์นี้ทิ้งแล้ว")

        # หั่น + embed ใหม่
        chunks = parse_chunks(file_path)
        texts = [c["text"] for c in chunks]
        embeddings = model.encode(texts).tolist()

        # เพิ่ม file_mtime เข้า metadata เพื่อใช้เช็คครั้งต่อไป
        metadatas = []
        for c in chunks:
            meta = dict(c["metadata"])
            meta["file_mtime"] = current_mtime
            metadatas.append(meta)

        collection.add(
            ids=[c["id"] for c in chunks],
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )
        print(f"   ✅ เพิ่ม {len(chunks)} chunks ใหม่เรียบร้อย")

    print(f"\n🎉 Re-index เสร็จสิ้น! อัปเดตทั้งหมด {len(changed_files)} ไฟล์")


if __name__ == "__main__":
    main()