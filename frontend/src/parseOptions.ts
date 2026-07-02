import type { ChatOption } from "./types";

/**
 * แยก syntax [OPTIONS:value1:label1|value2:label2|...] ออกจากข้อความ
 * ตรงกับ chat_service.py และ ui/components.py:24-59 (get_chat_bubble_html)
 */
export function parseOptions(message: string): { text: string; options: ChatOption[] } {
  const match = message.match(/\[OPTIONS:(.*?)\]/);
  if (!match || match.index === undefined) {
    return { text: message.trim(), options: [] };
  }

  const options: ChatOption[] = match[1]
    .split("|")
    .map((opt) => opt.trim())
    .filter(Boolean)
    .map((opt) => {
      const idx = opt.indexOf(":");
      if (idx === -1) return { value: opt, label: opt };
      return { value: opt.slice(0, idx).trim(), label: opt.slice(idx + 1).trim() };
    });

  const text = (message.slice(0, match.index) + message.slice(match.index + match[0].length)).trim();
  return { text, options };
}
