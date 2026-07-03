import importlib
import json
import os
import queue
import threading
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import backend.main as backend_main


def _parse_sse(text: str):
    """แปลง SSE stream text เป็น list ของ (event_type, data)"""
    events = []
    for block in text.strip().split("\n\n"):
        if not block:
            continue
        event_type = None
        data = None
        for line in block.split("\n"):
            if line.startswith("event: "):
                event_type = line[len("event: "):]
            elif line.startswith("data: "):
                data = json.loads(line[len("data: "):])
        if event_type is not None:
            events.append((event_type, data))
    return events


class BackendChatEndpointTest(unittest.TestCase):
    """R3(a)(b): SSE framing สำหรับ happy path และ error path"""

    def setUp(self):
        self.client = TestClient(backend_main.app)

    def test_question_that_enters_rag_streams_logs_then_done(self):
        def fake_answer_question(question, graph, cache=None, conversation=None):
            print("[offline_gate] passed")
            print("[route] category: car_insurance")
            return "คำตอบจาก RAG"

        with patch(
            "backend.main.answer_question", side_effect=fake_answer_question
        ):
            resp = self.client.post(
                "/api/chat",
                json={"sessionId": "session-a", "question": "ประกันรถยนต์ชั้นหนึ่งคุ้มครองอะไรบ้าง"},
            )

        self.assertEqual(resp.status_code, 200)
        events = _parse_sse(resp.text)

        log_events = [e for e in events if e[0] == "log"]
        done_events = [e for e in events if e[0] == "done"]

        self.assertEqual(len(log_events), 2)
        self.assertEqual(log_events[0][1], "[offline_gate] passed")
        self.assertEqual(log_events[1][1], "[route] category: car_insurance")

        self.assertEqual(len(done_events), 1)
        self.assertEqual(done_events[0][1], "คำตอบจาก RAG")

        # done ต้องมาเป็น event สุดท้ายเสมอ
        self.assertEqual(events[-1][0], "done")

    def test_pipeline_exception_yields_error_event_not_http_500(self):
        def fake_answer_question(question, graph, cache=None, conversation=None):
            raise RuntimeError("pipeline exploded")

        with patch(
            "backend.main.answer_question", side_effect=fake_answer_question
        ):
            resp = self.client.post(
                "/api/chat",
                json={"sessionId": "session-b", "question": "คำถามอะไรก็ได้"},
            )

        self.assertEqual(resp.status_code, 200)
        events = _parse_sse(resp.text)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0][0], "error")
        self.assertEqual(events[0][1], "pipeline exploded")

    def test_session_cache_and_conversation_are_isolated_between_sessions(self):
        seen_sessions = []

        def fake_answer_question(question, graph, cache=None, conversation=None):
            # ระบุตัวตนของ session ผ่าน object identity ของ cache/conversation dict
            seen_sessions.append((id(cache), id(conversation)))
            cache[question] = "answered"
            conversation["category"] = "car_insurance"
            return "ok"

        backend_main._sessions.clear()

        with patch(
            "backend.main.answer_question", side_effect=fake_answer_question
        ):
            self.client.post(
                "/api/chat",
                json={"sessionId": "session-x", "question": "q1"},
            )
            self.client.post(
                "/api/chat",
                json={"sessionId": "session-y", "question": "q1"},
            )

        self.assertEqual(len(seen_sessions), 2)
        cache_id_x, conv_id_x = seen_sessions[0]
        cache_id_y, conv_id_y = seen_sessions[1]

        self.assertNotEqual(cache_id_x, cache_id_y)
        self.assertNotEqual(conv_id_x, conv_id_y)

        session_x = backend_main._sessions["session-x"]
        session_y = backend_main._sessions["session-y"]

        self.assertIn("q1", session_x["cache"])
        self.assertIn("q1", session_y["cache"])
        self.assertIsNot(session_x["cache"], session_y["cache"])
        self.assertIsNot(session_x["conversation"], session_y["conversation"])

    def test_broad_offline_question_does_not_invoke_graph(self):
        """R3(d): ยืนยันว่า wiring backend ไม่ทำให้คำถามกว้าง/offline หลุดเข้า graph จริง

        ใช้ answer_question ตัวจริง (ไม่ mock) แต่ mock ที่ตัว _graph.invoke แทน
        เพื่อพิสูจน์ว่า flow จริงของ chat_service ไม่เรียก graph สำหรับคำถามกว้างในโดเมน
        """
        backend_main._sessions.clear()

        with patch.object(
            backend_main._graph, "invoke", side_effect=AssertionError("graph.invoke should not be called")
        ):
            resp = self.client.post(
                "/api/chat",
                json={"sessionId": "session-broad", "question": "ประกันชีวิต"},
            )

        self.assertEqual(resp.status_code, 200)
        events = _parse_sse(resp.text)

        # ต้องไม่มี error event เลย (ถ้า graph.invoke ถูกเรียกจริง จะได้ AssertionError
        # หลุดออกมาเป็น event "error" แทน) และ event สุดท้ายต้องเป็น done
        error_events = [e for e in events if e[0] == "error"]
        self.assertEqual(error_events, [])
        self.assertEqual(events[-1][0], "done")


class BackendPipelineConcurrencyTest(unittest.TestCase):
    """R1: _run_pipeline ต้อง serialize กันด้วย lock กัน stdout redirect ปนกันข้าม thread

    จำลอง 2 request วิ่งพร้อมกัน โดยบังคับ interleaving แบบ overlap (ไม่ nested)
    ซึ่งเป็นรูปแบบที่ทำให้ contextlib.redirect_stdout พังถ้าไม่มี lock:
    thread A enter redirect -> print line1 -> thread B enter redirect (ซ้อนขณะ A ยังไม่ exit)
    -> thread A exit (คืน sys.stdout ให้ค่าที่ A เคย save ไว้) -> thread B print ต่อ
    ถ้าไม่มี lock, บรรทัด log ของ B จะไปโผล่ผิด queue หรือหายไปเข้า real stdout
    """

    def setUp(self):
        self._orig_answer_question = backend_main.answer_question

    def tearDown(self):
        backend_main.answer_question = self._orig_answer_question

    def test_overlapping_requests_do_not_cross_contaminate_logs(self):
        gate_a_entered = threading.Event()
        gate_b_entered = threading.Event()
        gate_a_may_exit = threading.Event()

        qA: "queue.Queue" = queue.Queue()
        qB: "queue.Queue" = queue.Queue()

        # เก็บว่า answer_question ตัวไหนถูกเรียกตอนไหน เพื่อพิสูจน์ว่า lock บังคับให้รันทีละอัน
        call_order = []

        def fake_A(question, graph, cache=None, conversation=None):
            call_order.append("A-start")
            print("A-line1")
            gate_a_entered.set()
            # รอให้ B "พยายาม" เข้ามาแทรก ถ้า lock ทำงานถูกต้อง B จะบล็อกรออยู่ตรงนี้
            # ไม่สามารถเข้ามา print แทรกระหว่างที่ A ยังไม่ปล่อย lock
            gate_a_may_exit.wait(timeout=2)
            print("A-line2")
            call_order.append("A-end")
            return "A-answer"

        def fake_B(question, graph, cache=None, conversation=None):
            call_order.append("B-start")
            print("B-line1")
            print("B-line2")
            call_order.append("B-end")
            return "B-answer"

        def run_A():
            backend_main.answer_question = fake_A
            session = {"cache": {}, "conversation": {}}
            backend_main._run_pipeline("qA", session, qA)

        def run_B():
            gate_a_entered.wait(timeout=2)
            # ปล่อยให้ A ไป exit ได้ไม่นานหลังจากนี้ (เพื่อสร้าง overlap window)
            threading.Timer(0.05, gate_a_may_exit.set).start()
            backend_main.answer_question = fake_B
            session = {"cache": {}, "conversation": {}}
            backend_main._run_pipeline("qB", session, qB)

        thread_a = threading.Thread(target=run_A)
        thread_b = threading.Thread(target=run_B)
        thread_b.start()
        thread_a.start()
        thread_a.join(timeout=5)
        thread_b.join(timeout=5)

        def drain(q):
            items = []
            while not q.empty():
                items.append(q.get())
            return items

        items_a = drain(qA)
        items_b = drain(qB)

        # แต่ละ stream ต้องมีแค่ log ของตัวเอง ไม่ปนกัน
        log_lines_a = [payload for kind, payload in items_a if kind == "log"]
        log_lines_b = [payload for kind, payload in items_b if kind == "log"]

        self.assertEqual(log_lines_a, ["A-line1", "A-line2"])
        self.assertEqual(log_lines_b, ["B-line1", "B-line2"])

        # แต่ละ stream ต้องได้ done answer ของตัวเอง ไม่ใช่ของอีกฝั่ง
        done_a = [payload for kind, payload in items_a if kind == "done"]
        done_b = [payload for kind, payload in items_b if kind == "done"]
        self.assertEqual(done_a, ["A-answer"])
        self.assertEqual(done_b, ["B-answer"])

        # lock ต้อง serialize การรัน: B ต้องรอ A จบสนิทก่อน (A-end ก่อน B-start)
        # เพราะ run_B พยายามเริ่มก่อน (thread_b.start() มาก่อน) แต่ต้องรอ lock ที่ A ถืออยู่
        self.assertEqual(call_order, ["A-start", "A-end", "B-start", "B-end"])


class BackendSessionLruEvictionTest(unittest.TestCase):
    """R2: _sessions ต้องจำกัดขนาดด้วย LRU กัน memory leak"""

    def setUp(self):
        self._orig_sessions = backend_main._sessions
        backend_main._sessions = type(backend_main._sessions)()

    def tearDown(self):
        backend_main._sessions = self._orig_sessions

    def test_creating_more_than_max_sessions_evicts_oldest(self):
        max_sessions = backend_main.MAX_SESSIONS

        for i in range(max_sessions):
            backend_main._get_session(f"session-{i}")

        self.assertEqual(len(backend_main._sessions), max_sessions)
        self.assertIn("session-0", backend_main._sessions)

        # เกิน MAX ไปหนึ่ง session ใหม่ -> ตัวเก่าสุด (session-0) ต้องถูก evict
        backend_main._get_session("session-overflow")

        self.assertEqual(len(backend_main._sessions), max_sessions)
        self.assertNotIn("session-0", backend_main._sessions)
        self.assertIn("session-overflow", backend_main._sessions)
        # session ที่สร้างไล่ๆ กันมาแต่ยังไม่เก่าสุดต้องยังอยู่
        self.assertIn(f"session-{max_sessions - 1}", backend_main._sessions)

    def test_accessing_existing_session_refreshes_recency_and_avoids_eviction(self):
        max_sessions = backend_main.MAX_SESSIONS

        for i in range(max_sessions):
            backend_main._get_session(f"session-{i}")

        # เข้าถึง session-0 ซ้ำ (ทำให้กลาย "ล่าสุด" ไม่ใช่ตัวเก่าสุดแล้ว)
        backend_main._get_session("session-0")

        # ตอนนี้ session-1 คือเก่าสุดจริง ไม่ใช่ session-0
        backend_main._get_session("session-overflow")

        self.assertEqual(len(backend_main._sessions), max_sessions)
        self.assertIn("session-0", backend_main._sessions)  # รอดเพราะเพิ่ง access
        self.assertNotIn("session-1", backend_main._sessions)  # ถูก evict แทน
        self.assertIn("session-overflow", backend_main._sessions)

    def test_session_data_is_preserved_across_lru_access(self):
        session = backend_main._get_session("session-keep")
        session["cache"]["some_key"] = "some_value"

        # เข้าถึงซ้ำ ต้องได้ dict เดิม (object เดียวกัน) ไม่ถูกสร้างใหม่
        session_again = backend_main._get_session("session-keep")
        self.assertIs(session, session_again)
        self.assertEqual(session_again["cache"]["some_key"], "some_value")


def _fake_getenv_missing_openrouter_key(real_getenv):
    """คืน os.getenv ปลอมที่ตอบ None เฉพาะ OPENROUTER_API_KEY แต่ delegate ตัวแปรอื่น
    (เช่น CORS_ALLOWED_ORIGINS) ไปหา os.getenv จริง กัน test R4 ไปพังการอ่าน env อื่น
    """

    def _fake(name, default=None):
        if name == "OPENROUTER_API_KEY":
            return None
        return real_getenv(name, default)

    return _fake


def _fake_getenv_present_openrouter_key(real_getenv):
    def _fake(name, default=None):
        if name == "OPENROUTER_API_KEY":
            return "fake-key-value"
        return real_getenv(name, default)

    return _fake


class BackendConfigHealthTest(unittest.TestCase):
    """R4: startup ต้อง fail-fast (log ชัดเจน) เมื่อไม่มี OPENROUTER_API_KEY
    และ /api/health ต้องสะท้อนสถานะจริง ไม่โกหกว่า ok เสมอ

    ใช้ importlib.reload พร้อม patch("os.getenv") เฉพาะ OPENROUTER_API_KEY เพื่อจำลอง
    สถานะ "ไม่มี key" โดยไม่ไปยุ่งกับ os.environ จริง, ไฟล์ .env, หรือ env var อื่นที่
    backend.main อ่านด้วย (เช่น CORS_ALLOWED_ORIGINS ของ R7)
    """

    def tearDown(self):
        # reload กลับให้ backend_main ใช้ environment จริงเสมอหลัง test นี้จบ
        importlib.reload(backend_main)

    def test_health_reports_ok_when_key_present(self):
        real_getenv = os.getenv
        with patch("os.getenv", side_effect=_fake_getenv_present_openrouter_key(real_getenv)):
            importlib.reload(backend_main)
            self.assertTrue(backend_main._config_ready)

            client = TestClient(backend_main.app)
            resp = client.get("/api/health")

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "ok")
        self.assertTrue(body["config_ready"])

    def test_health_reports_degraded_when_key_missing(self):
        real_getenv = os.getenv
        with patch("os.getenv", side_effect=_fake_getenv_missing_openrouter_key(real_getenv)):
            importlib.reload(backend_main)
            self.assertFalse(backend_main._config_ready)

            client = TestClient(backend_main.app)
            resp = client.get("/api/health")

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "degraded")
        self.assertFalse(body["config_ready"])

    def test_startup_logs_actionable_warning_when_key_missing_and_never_logs_key_value(self):
        real_getenv = os.getenv
        with patch("os.getenv", side_effect=_fake_getenv_missing_openrouter_key(real_getenv)):
            with self.assertLogs("backend.main", level="WARNING") as cm:
                importlib.reload(backend_main)

        joined = "\n".join(cm.output)
        self.assertIn("OPENROUTER_API_KEY", joined)
        # ห้าม log ค่า key จริงๆ ออกมา (ในเคสนี้ getenv ถูก patch ให้คืน None อยู่แล้ว
        # แต่ตรวจเผื่อว่าไม่มีการพยายาม format ค่า key ลงข้อความ log)
        self.assertNotIn("fake-key-value", joined)


class BackendCorsConfigTest(unittest.TestCase):
    """R7: allowed CORS origin ต้องอ่านจาก env ได้ ไม่ hardcode ตายตัว"""

    def tearDown(self):
        importlib.reload(backend_main)

    def test_default_origin_is_vite_dev_server_when_env_not_set(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CORS_ALLOWED_ORIGINS", None)
            importlib.reload(backend_main)

        self.assertEqual(backend_main.ALLOWED_ORIGINS, ["http://localhost:5173"])

    def test_env_overrides_allowed_origins_and_supports_multiple(self):
        with patch.dict(
            os.environ,
            {"CORS_ALLOWED_ORIGINS": "http://example.com:3000, http://foo.com"},
        ):
            importlib.reload(backend_main)

        self.assertEqual(
            backend_main.ALLOWED_ORIGINS,
            ["http://example.com:3000", "http://foo.com"],
        )


class BackendSessionEndpointTest(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(backend_main.app)

    def test_new_session_returns_uuid(self):
        resp = self.client.post("/api/session")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("sessionId", body)
        self.assertTrue(len(body["sessionId"]) > 0)


if __name__ == "__main__":
    unittest.main()
