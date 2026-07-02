import base64
import html
from pathlib import Path

import streamlit as st


STYLE_PATH = Path(__file__).with_name("styles.css")
AI_AVATAR_PATH = Path(__file__).with_name("assets") / "ai_avatar.jpg"

USER_AVATAR = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>'

_ai_avatar_base64 = base64.b64encode(AI_AVATAR_PATH.read_bytes()).decode("ascii")
AI_AVATAR = (
    f'<img src="data:image/jpeg;base64,{_ai_avatar_base64}" alt="AI" '
    'style="width:100%;height:100%;object-fit:cover;border-radius:50%;">'
)

def load_styles():
    stylesheet = STYLE_PATH.read_text(encoding="utf-8")
    st.markdown(f"<style>{stylesheet}</style>", unsafe_allow_html=True)


def get_chat_bubble_html(role, message):
    role_class = "user" if role == "user" else "assistant"
    avatar_html = USER_AVATAR if role == "user" else AI_AVATAR
    
    import re
    options = []
    message_str = str(message).strip()
    
    match = re.search(r'\[OPTIONS:(.*?)\]', message_str)
    if match:
        options_text = match.group(1)
        options = [opt.strip() for opt in options_text.split('|') if opt.strip()]
        message_str = message_str[:match.start()] + message_str[match.end():]
        message_str = message_str.strip()
        
    safe_message = html.escape(message_str).replace("\n", "<br>")
    
    bubble_html = (
        f'<div class="chat-row {role_class}">'
        f'<div class="chat-avatar">{avatar_html}</div>'
        f'<div class="chat-bubble">{safe_message}</div>'
        f"</div>"
    )
    
    if options:
        buttons_html = '<div style="margin-top: 12px; display: flex; gap: 8px; flex-wrap: wrap;">'
        for opt in options:
            if ":" in opt:
                val, label = opt.split(":", 1)
            else:
                val = label = opt
            buttons_html += f'<button class="custom-reply-btn" data-reply="{html.escape(val.strip())}">{html.escape(label.strip())}</button>'
        buttons_html += '</div>'
        bubble_html = bubble_html[:-12] + buttons_html + "</div></div>"
        
    return bubble_html

def render_chat_bubble(role, message):
    st.markdown(get_chat_bubble_html(role, message), unsafe_allow_html=True)

def get_pipeline_logs_html(logs_str):
    if not logs_str:
        return ""
    steps = []
    lines = logs_str.split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if "[offline_menu]" in line:
            if "car_insurance" in line:
                detail = "ประกันรถยนต์"
            elif "life_insurance" in line:
                detail = "ประกันชีวิต"
            else:
                detail = line.split("]", 1)[-1].strip()
            steps.append(("⚡", "Offline", detail, "offline"))
        elif "[offline_gate]" in line:
            steps.append(("🛡️", "Offline Gate", "ตอบด้วยกฎ offline", "offline"))
        elif "[context]" in line:
            if "car_insurance" in line:
                detail = "ใช้บริบทประกันรถยนต์"
            elif "life_insurance" in line:
                detail = "ใช้บริบทประกันชีวิต"
            else:
                detail = line.split("]", 1)[-1].strip()
            steps.append(("🧩", "Context", detail, "context"))
        elif "[cache_hit]" in line:
            steps.append(("⚡", "Cache", "ใช้คำตอบเดิม", "cache"))
        elif "[route_node]" in line:
            if "car_insurance" in line:
                steps.append(("💬", "Route", "ประกันรถยนต์", "route"))
            elif "life_insurance" in line:
                steps.append(("💬", "Route", "ประกันชีวิต", "route"))
            elif "general" in line:
                steps.append(("💬", "Route", "ทั่วไป", "route"))
            else:
                steps.append(("💬", "Route", line.split("]", 1)[-1].strip(), "route"))
        elif "[search_node]" in line:
            detail = line.split("]", 1)[-1].strip()
            steps.append(("🔍", "Search", detail, "search"))
        elif "[rewrite_node]" in line:
            detail = line.split("]", 1)[-1].strip()
            steps.append(("✏️", "Rewrite", detail or "Rewritten", "rewrite"))
        elif "[generate_node]" in line:
            detail = line.split("]", 1)[-1].strip()
            steps.append(("✨", "Generate", detail or "gpt-4o-mini", "generate"))
        elif "[hallucination_check_node]" in line:
            if "✅ grounded" in line:
                steps.append(("🛡️", "Check", "✅ Grounded", "check-pass"))
            elif "❌ hallucinated" in line:
                steps.append(("🛡️", "Check", "❌ Hallucinated", "check-fail"))
            elif "fallback" in line:
                steps.append(("🛡️", "Check", "⚠️ Fallback", "check-warn"))
            else:
                steps.append(("🛡️", "Check", line.split("]", 1)[-1].strip(), "check"))
    if not steps:
        return ""
    
    html_parts = []
    for i, (icon, title, detail, step_type) in enumerate(steps):
        is_last = (i == len(steps) - 1)
        if "check-pass" in step_type:
            dot_color = "#10B981"
        elif "check-fail" in step_type:
            dot_color = "#EF4444"
        elif "check-warn" in step_type:
            dot_color = "#F59E0B"
        else:
            dot_color = "#6366F1"
        r, g, b = int(dot_color[1:3], 16), int(dot_color[3:5], 16), int(dot_color[5:7], 16)
        line_html = "" if is_last else f'<div style="position:absolute;left:5.5px;top:16px;bottom:-6px;width:1.5px;background:{dot_color};opacity:0.3;"></div>'
        html_parts.append(f"""<div style="display:flex;gap:8px;padding:0 0 6px 0;position:relative;"><div style="position:relative;flex-shrink:0;width:14px;display:flex;flex-direction:column;align-items:center;padding-top:4px;"><div style="width:12px;height:12px;border-radius:50%;background:rgba({r},{g},{b},0.15);border:2px solid {dot_color};z-index:2;box-shadow:0 0 6px rgba({r},{g},{b},0.4);"></div>{line_html}</div><div style="flex:1;background:#0F172A;border:1px solid rgba(255,255,255,0.06);border-radius:12px;padding:6px 10px;box-shadow:0 2px 8px rgba(0,0,0,0.1);"><div style="display:flex;justify-content:space-between;align-items:center;"><span style="color:#F8FAFC;font-weight:600;font-size:0.8em;font-family:'Space Grotesk',sans-serif;">{icon} {title}</span><span style="color:{dot_color};font-size:0.7em;font-weight:600;padding:2px 8px;border-radius:10px;background:rgba({r},{g},{b},0.1);">Step {i+1}</span></div><div style="color:#94A3B8;font-size:0.75em;line-height:1.4;margin-top:2px;font-family:'DM Sans',sans-serif;">{detail}</div></div></div>""")
    
    return "".join(html_parts)

def render_pipeline_logs(logs_str):
    html = get_pipeline_logs_html(logs_str)
    if html:
        st.markdown(html, unsafe_allow_html=True)
