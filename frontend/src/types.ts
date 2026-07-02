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
}
