export interface ChatOption {
  value: string;
  label: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  text: string;
  options?: ChatOption[];
}

export interface LogStep {
  icon: string;
  title: string;
  detail: string;
  type: string;
  /** true = เส้นแบ่งบอกจุดเริ่มคำถามใหม่ ไม่นับเป็น step และไม่มีเลข Step กำกับ */
  isTurnMarker?: boolean;
}
