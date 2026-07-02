# Hybrid Router Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ใช้ LLM จำแนกหมวดเฉพาะเมื่อ Offline Router ตัดสินคำถามประกันไม่ได้

**Architecture:** `offline_gate.py` กรองนอกเรื่องก่อน จากนั้น `query_router.py` ใช้ keyword ฟรี ถ้ายังได้ `general` จึงเรียก LLM หนึ่งครั้ง คำถามกว้างยังตอบขอรายละเอียดโดยไม่เรียก LLM และ `chat_service.py` ตรวจ cache ก่อนเรียก router

**Tech Stack:** Python 3.9, unittest, unittest.mock, OpenAI-compatible API ผ่าน OpenRouter

---

### Task 1: ให้คำศัพท์งานซ่อมผ่าน Offline Gate

**Files:**
- Modify: `offline_gate.py`
- Test: `test/test_offline_gate.py`

- [ ] **Step 1: เขียนเทสที่ต้องล้มก่อน**

เพิ่มใน `OfflineGateTest`:

```python
def test_repair_shop_question_goes_to_rag(self):
    answer = check_offline_gate("ซ่อมห้างกับซ่อมอู่ต่างกันยังไง")
    self.assertIsNone(answer)
```

- [ ] **Step 2: รันเทสและยืนยันว่า FAIL**

```powershell
python -m unittest discover -s test -p "test_offline_gate.py" -v
```

ผลที่คาด: เทสใหม่ FAIL เพราะระบบตอบว่าอยู่นอกขอบเขต

- [ ] **Step 3: เพิ่มคำที่บอกว่าเป็นเรื่องประกันรถ**

เพิ่มใน `INSURANCE_KEYWORDS`:

```python
"ซ่อมห้าง",
"ซ่อมอู่",
```

- [ ] **Step 4: รันเทสเดิมอีกครั้ง**

ผลที่คาด: ทุกเทสใน `test_offline_gate.py` ผ่าน

### Task 2: เพิ่ม LLM fallback ใน Query Router

**Files:**
- Modify: `query_router.py`
- Test: `test/test_offline_router.py`

- [ ] **Step 1: เขียนเทสว่า LLM ถูกเรียกเฉพาะคำถามกำกวม**

เพิ่มใน `OfflineRouterTest`:

```python
@patch("query_router.client.chat.completions.create")
def test_ambiguous_car_question_uses_llm_once(self, mock_create):
    mock_create.return_value.choices[0].message.content = "car_insurance"

    category = route_query("ประกัน 2+ กับ 3+ ต่างกันยังไง")

    self.assertEqual(category, "car_insurance")
    mock_create.assert_called_once()

@patch("query_router.client.chat.completions.create")
def test_invalid_llm_label_returns_general(self, mock_create):
    mock_create.return_value.choices[0].message.content = "unknown"

    category = route_query("ประกันรูปแบบนี้เหมาะกับใคร")

    self.assertEqual(category, "general")

@patch("query_router.client.chat.completions.create")
def test_llm_error_returns_general(self, mock_create):
    mock_create.side_effect = RuntimeError("API unavailable")

    category = route_query("ประกันรูปแบบนี้เหมาะกับใคร")

    self.assertEqual(category, "general")
```

- [ ] **Step 2: รันเทสและยืนยันว่าเทสใหม่ FAIL**

```powershell
python -m unittest discover -s test -p "test_offline_router.py" -v
```

ผลที่คาด: เทสคำถาม `2+ กับ 3+` FAIL เพราะ router เดิมคืน `general`

- [ ] **Step 3: เพิ่ม prompt, model และฟังก์ชัน LLM fallback**

เพิ่มเหนือ `route_query`:

```python
ROUTER_MODEL = "openai/gpt-4o-mini"

ROUTER_SYSTEM_PROMPT = """คุณเป็นระบบจำแนกหมวดหมู่คำถามลูกค้าประกันภัย
ตอบเพียงหนึ่งคำจาก car_insurance, life_insurance, general
car_insurance คือเรื่องประกันรถ การเคลมรถ อุบัติเหตุ 2+ 3+ ซ่อมห้าง และซ่อมอู่
life_insurance คือเรื่องประกันชีวิต ผู้รับประโยชน์ การเวนคืน และกรมธรรม์ชีวิต
general คือคำถามไม่เกี่ยวข้องหรือข้อมูลไม่พอจำแนก"""


def _route_with_llm(question: str) -> str:
    try:
        response = client.chat.completions.create(
            model=ROUTER_MODEL,
            messages=[
                {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ],
            temperature=0,
            max_tokens=10,
        )
        label = response.choices[0].message.content.strip().lower()
    except Exception:
        return "general"

    if label not in VALID_CATEGORIES:
        return "general"

    return label
```

- [ ] **Step 4: แยก Offline Router และประกอบเป็น Hybrid**

เปลี่ยน `route_query` เดิมเป็น:

```python
def _route_offline(normalized_question: str) -> str:
    for keyword in CAR_KEYWORDS:
        if keyword in normalized_question:
            return "car_insurance"

    for keyword in LIFE_KEYWORDS:
        if keyword in normalized_question:
            return "life_insurance"

    return "general"


def route_query(question: str) -> str:
    normalized_question = _normalize(question)

    if normalized_question in VAGUE_CATEGORY_TERMS:
        return "general"

    offline_category = _route_offline(normalized_question)
    if offline_category != "general":
        return offline_category

    return _route_with_llm(question)
```

เพิ่ม `"มีประกันแบบไหนบ้าง"` ใน `VAGUE_CATEGORY_TERMS` เพื่อรักษาพฤติกรรมเดิมที่ไม่เรียก LLM

- [ ] **Step 5: รัน router tests**

ผลที่คาด: เทสเดิมยืนยันว่าคำถามชัดไม่เรียก LLM และเทสใหม่ทั้งหมดผ่าน

### Task 3: ให้ cache ทำงานก่อน Hybrid Router

**Files:**
- Modify: `chat_service.py`
- Test: `test/test_chat_cache.py`

- [ ] **Step 1: เขียนเทสว่าคำถามซ้ำไม่จำแนกหมวดซ้ำ**

เพิ่ม import `patch` และเพิ่มเทส:

```python
@patch("chat_service.route_query", return_value="car_insurance")
def test_cached_question_routes_only_once(self, mock_route_query):
    graph = FakeGraph()
    cache = {}

    answer_question("ประกัน 2+ ต่างจาก 3+ อย่างไร", graph, cache)
    answer_question("ประกัน 2+ ต่างจาก 3+ อย่างไร", graph, cache)

    self.assertEqual(mock_route_query.call_count, 1)
    self.assertEqual(graph.invoke_count, 1)
```

- [ ] **Step 2: รันเทสและยืนยันว่า FAIL**

```powershell
python -m unittest discover -s test -p "test_chat_cache.py" -v
```

ผลที่คาด: `route_query` ถูกเรียก 2 ครั้ง

- [ ] **Step 3: ย้าย cache lookup ไปไว้ก่อน `route_query(question)`**

ใน `answer_question` หลัง broad-term checks ให้สร้าง `cache_key` และคืนคำตอบจาก cache ก่อนเรียก router จากนั้นลบ cache lookup ชุดเดิมด้านล่าง

```python
cache_key = _make_cache_key(question)

if cache is not None and cache_key in cache:
    return cache[cache_key]

category = route_query(question)
```

- [ ] **Step 4: รัน cache tests**

ผลที่คาด: router และ graph ถูกเรียกอย่างละหนึ่งครั้ง

### Task 4: ตรวจระบบรวม

**Files:**
- Test: `test/test_chat_service.py`
- Test: ชุดเทสทั้งหมดใน `test/`

- [ ] **Step 1: รันเทสเฉพาะส่วนที่แก้**

```powershell
python -m unittest discover -s test -p "test_offline_gate.py" -v
python -m unittest discover -s test -p "test_offline_router.py" -v
python -m unittest discover -s test -p "test_chat_cache.py" -v
python -m unittest discover -s test -p "test_chat_service.py" -v
```

- [ ] **Step 2: รันเทสทั้งหมด**

```powershell
python -m unittest discover -s test -v
```

ผลที่คาด: ทุกเทสผ่าน และไม่มีการเรียก API จริงจาก unit tests

## หมายเหตุเรื่อง Git

ยังไม่มี `.git` ใน `D:\GitHub\AdvanceRAG` จึงไม่มีขั้น commit ในแผนนี้ หากเปิดใช้ Git ภายหลัง ให้ commit แยกหลังจบแต่ละ Task

