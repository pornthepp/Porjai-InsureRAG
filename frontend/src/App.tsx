import { useEffect, useRef, useState } from "react";
import "./App.css";
import ChatBubble from "./components/ChatBubble";
import LogPanel from "./components/LogPanel";
import { parseOptions } from "./parseOptions";
import { parseLogLine } from "./parseLogLine";
import { streamChat } from "./api";
import type { ChatMessage, LogStep } from "./types";
import aiAvatar from "./assets/ai_avatar.jpg";

const WELCOME_MESSAGE =
  "สวัสดีค่ะ ยินดีให้บริการเรื่องประกันภัยค่ะ สนใจประกันรถยนต์หรือประกันชีวิตคะ พิมพ์คำถามของคุณได้เลยค่ะ" +
  "[OPTIONS:ประกันรถยนต์:🚗 ประกันรถยนต์|ประกันชีวิต:❤️ ประกันชีวิต]";

function buildMessage(role: ChatMessage["role"], raw: string): ChatMessage {
  const { text, options } = parseOptions(raw);
  return { role, text, options };
}

export default function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([buildMessage("assistant", WELCOME_MESSAGE)]);
  const [pending, setPending] = useState(false);
  const [logSteps, setLogSteps] = useState<LogStep[]>([]);
  const [rawLogs, setRawLogs] = useState("");
  const [inputValue, setInputValue] = useState("");

  const chatEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  // ref-based in-flight guard: state `pending` มาจาก closure เก่าตอน event handler ถูกสร้าง
  // ถ้ากด Enter/ปุ่มส่งรัวสองทีในเฟรมเดียวกัน (ก่อน React re-render) การเช็ค `pending` จาก state
  // เพียงอย่างเดียวจะผ่าน guard ทั้งคู่ ref อ่าน/เขียนแบบ synchronous เลยกันซ้อนได้จริง
  const inFlightRef = useRef(false);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, pending, logSteps]);

  async function sendMessage(question: string) {
    if (!question.trim() || inFlightRef.current) return;

    inFlightRef.current = true;
    setMessages((prev) => [...prev, buildMessage("user", question)]);
    setInputValue("");
    setPending(true);
    // สะสม log ต่อกันทั้งบทสนทนา (ไม่ล้างทุกคำถาม) แล้วคั่นด้วยเส้นแบ่งบอกจุดเริ่มคำถามใหม่
    // เพื่อให้เห็นว่า step ไหนเป็นของคำถามไหน
    setLogSteps((prev) => [
      ...prev,
      { icon: "🗨️", title: "คำถามใหม่", detail: question, type: "turn", isTurnMarker: true },
    ]);
    setRawLogs((prev) => (prev ? `${prev}\n--- ${question} ---` : `--- ${question} ---`));

    try {
      await streamChat(question, (event) => {
        if (event.type === "log") {
          setRawLogs((prev) => (prev ? `${prev}\n${event.data}` : event.data));
          const step = parseLogLine(event.data);
          if (step) setLogSteps((prev) => [...prev, step]);
        } else if (event.type === "done") {
          setMessages((prev) => [...prev, buildMessage("assistant", event.data)]);
        } else if (event.type === "error") {
          setMessages((prev) => [
            ...prev,
            buildMessage("assistant", `ขออภัยค่ะ เกิดข้อผิดพลาด: ${event.data}`),
          ]);
        }
      });
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        buildMessage("assistant", `ขออภัยค่ะ เชื่อมต่อระบบไม่ได้: ${(err as Error).message}`),
      ]);
    } finally {
      // เคลียร์ pending/guard เสมอไม่ว่า stream จะจบแบบมี done/error หรือจบเฉยๆ โดยไม่มี event
      // ป้องกัน input ค้างล็อกถาวรถ้า backend ปิด stream โดยไม่ส่ง done/error
      inFlightRef.current = false;
      setPending(false);
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(inputValue);
    }
  }

  return (
    <div className="page">
      <div className="header">
        <span className="header-star">✧</span>
        <span className="header-title">คุยกับน้องพอใจ</span>
      </div>

      <div className="columns">
        <div className="panel chat-panel">
          <div className="panel-header">
            <span>💬</span>
            <span className="panel-title">Chat</span>
            <span className="online-badge">
              <span className="online-dot" />
              Online
            </span>
          </div>

          <div className="chat-container">
            {messages.map((m, i) => (
              <ChatBubble key={i} message={m} onOptionClick={sendMessage} disabled={pending} />
            ))}
            {pending && (
              <div className="chat-row assistant">
                <div className="chat-avatar">
                  <img
                    src={aiAvatar}
                    alt="AI"
                    style={{ width: "100%", height: "100%", objectFit: "cover", borderRadius: "50%" }}
                  />
                </div>
                <div className="chat-bubble chat-thinking-bubble">
                  <div className="chat-dot" />
                  <div className="chat-dot" />
                  <div className="chat-dot" />
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          <div className="chat-input-row">
            <textarea
              ref={inputRef}
              className="chat-input"
              placeholder="พิมพ์คำถามของคุณ..."
              value={inputValue}
              disabled={pending}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
            />
            <button
              type="button"
              className="send-btn"
              disabled={pending || !inputValue.trim()}
              onClick={() => sendMessage(inputValue)}
              aria-label="ส่ง"
            >
              ➤
            </button>
          </div>
        </div>

        <div className="panel log-panel">
          <LogPanel steps={logSteps} thinking={pending} rawLogs={rawLogs} />
        </div>
      </div>
    </div>
  );
}
