import type { LogStep } from "./types";

/**
 * แปลงบรรทัด log ดิบจาก backend (print() ใน chat_service.py / graph_nodes.py)
 * เป็น LogStep แสดงในพาแนล "กระบวนการคิด" — ตรงกับ ui/components.py:64-119 (get_pipeline_logs_html)
 * ลำดับการเช็คต้องตรงกับต้นฉบับ เพราะเป็น if/elif แบบ first-match-wins
 */
export function parseLogLine(rawLine: string): LogStep | null {
  const line = rawLine.trim();
  if (!line) return null;

  const afterTag = () => line.split("]").slice(1).join("]").trim();

  if (line.includes("[offline_menu]")) {
    let detail: string;
    if (line.includes("car_insurance")) detail = "ประกันรถยนต์";
    else if (line.includes("life_insurance")) detail = "ประกันชีวิต";
    else detail = afterTag();
    return { icon: "⚡", title: "Offline", detail, type: "offline" };
  }

  if (line.includes("[offline_gate]")) {
    return { icon: "🛡️", title: "Offline Gate", detail: "ตอบด้วยกฎ offline", type: "offline" };
  }

  if (line.includes("[context]")) {
    let detail: string;
    if (line.includes("car_insurance")) detail = "ใช้บริบทประกันรถยนต์";
    else if (line.includes("life_insurance")) detail = "ใช้บริบทประกันชีวิต";
    else detail = afterTag();
    return { icon: "🧩", title: "Context", detail, type: "context" };
  }

  if (line.includes("[cache_hit]")) {
    return { icon: "⚡", title: "Cache", detail: "ใช้คำตอบเดิม", type: "cache" };
  }

  if (line.includes("[route_node]")) {
    if (line.includes("car_insurance")) return { icon: "💬", title: "Route", detail: "ประกันรถยนต์", type: "route" };
    if (line.includes("life_insurance")) return { icon: "💬", title: "Route", detail: "ประกันชีวิต", type: "route" };
    if (line.includes("general")) return { icon: "💬", title: "Route", detail: "ทั่วไป", type: "route" };
    return { icon: "💬", title: "Route", detail: afterTag(), type: "route" };
  }

  if (line.includes("[search_node]")) {
    return { icon: "🔍", title: "Search", detail: afterTag(), type: "search" };
  }

  if (line.includes("[rewrite_node]")) {
    const detail = afterTag();
    return { icon: "✏️", title: "Rewrite", detail: detail || "Rewritten", type: "rewrite" };
  }

  if (line.includes("[generate_node]")) {
    const detail = afterTag();
    return { icon: "✨", title: "Generate", detail: detail || "gpt-4o-mini", type: "generate" };
  }

  if (line.includes("[hallucination_check_node]")) {
    if (line.includes("✅ grounded")) return { icon: "🛡️", title: "Check", detail: "✅ Grounded", type: "check-pass" };
    if (line.includes("❌ hallucinated")) return { icon: "🛡️", title: "Check", detail: "❌ Hallucinated", type: "check-fail" };
    if (line.includes("fallback")) return { icon: "🛡️", title: "Check", detail: "⚠️ Fallback", type: "check-warn" };
    return { icon: "🛡️", title: "Check", detail: afterTag(), type: "check" };
  }

  return null;
}

export function dotColorForType(type: string): string {
  if (type.includes("check-pass")) return "#10B981";
  if (type.includes("check-fail")) return "#EF4444";
  if (type.includes("check-warn")) return "#F59E0B";
  return "#6366F1";
}
