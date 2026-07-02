import streamlit as st
import io
import contextlib
from ui import load_styles, render_chat_bubble, render_pipeline_logs, get_chat_bubble_html, get_pipeline_logs_html, AI_AVATAR
import time
from streamlit.components.v1 import html as st_html

# --- ตั้งค่าโหมดทดสอบ UI (ข้ามการโหลด Model) ---
# เปลี่ยนเป็น False เมื่อต้องการใช้งานโมเดลจริง
UI_TEST_MODE = False

if not UI_TEST_MODE:
    from graph_builder import build_graph
    from chat_service import answer_question

WELCOME_MESSAGE = (
    "สวัสดีค่ะ ยินดีให้บริการเรื่องประกันภัยค่ะ "
    "สนใจประกันรถยนต์หรือประกันชีวิตคะ "
    "พิมพ์คำถามของคุณได้เลยค่ะ"
    "[OPTIONS:ประกันรถยนต์:🚗 ประกันรถยนต์|ประกันชีวิต:❤️ ประกันชีวิต]"
)

st.set_page_config(page_title="คุยกับน้องพอใจ", layout="wide")
CHAT_PANEL_HEIGHT = 440
PIPELINE_LOG_HEIGHT = 320
RAW_LOG_HEIGHT = 100


# โหลดกราฟครั้งเดียว แคชไว้
@st.cache_resource
def get_graph():
    if UI_TEST_MODE:
        return None
    return build_graph()

app = get_graph()

# Session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [("assistant", WELCOME_MESSAGE)]
if "answer_cache" not in st.session_state:
    st.session_state.answer_cache = {}
if "conversation" not in st.session_state:
    st.session_state.conversation = {}
if "last_logs" not in st.session_state:
    st.session_state.last_logs = ""
if "pending_question" not in st.session_state:
    st.session_state.pending_question = None

def queue_question(manual_text=None):
    if manual_text:
        question = manual_text
    else:
        question = st.session_state.get("chat_input_value")
    if not question:
        return
    st.session_state.chat_history.append(("user", question))
    st.session_state.pending_question = question


load_styles()



# ===================== HEADER =====================
st.markdown("""<div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;"><span style="color:#7C3AED;font-size:1.4em;">✧</span><span style="font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:1.4em;background:linear-gradient(135deg, #F8FAFC, #94A3B8);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">คุยกับน้องพอใจ</span></div>""", unsafe_allow_html=True)

# ===================== LAYOUT: Chat (left) | Pipeline Log (right) =====================
# --- 1. RENDER LAYOUT FIRST ---
col_chat, col_log = st.columns([1, 1], gap="large")

with col_chat:
    st.markdown("""<div style="background:#1E293B;border:1px solid rgba(255,255,255,0.05);border-bottom:none;border-radius:16px 16px 0 0;padding:12px 18px;display:flex;align-items:center;gap:8px;box-shadow:0 -4px 20px -2px rgba(0,0,0,0.2);position:relative;z-index:1;"><span style="color:#7C3AED;font-size:0.9em;">💬</span><span style="color:#F8FAFC;font-weight:600;font-size:0.85em;font-family:'Space Grotesk',sans-serif;">Chat</span><span style="margin-left:auto;display:flex;align-items:center;gap:6px;color:#10B981;font-size:0.75em;font-family:'DM Sans',sans-serif;font-weight:600;"><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#10B981;box-shadow:0 0 8px rgba(16,185,129,0.6);animation:pulse 2s infinite;"></span>Online</span></div>""", unsafe_allow_html=True)
    chat_container = st.container(height=CHAT_PANEL_HEIGHT, border=True)
    user_question = st.chat_input(
        "พิมพ์คำถามของคุณ...",
        key="chat_input_value",
        on_submit=queue_question,
        disabled=bool(st.session_state.pending_question)
    )

with col_log:
    st.markdown("""<div style="background:#1E293B;border:1px solid rgba(255,255,255,0.05);border-bottom:none;border-radius:16px 16px 0 0;padding:12px 18px;display:flex;align-items:center;gap:8px;box-shadow:0 -4px 20px -2px rgba(0,0,0,0.2);position:relative;z-index:1;"><span style="color:#7C3AED;font-size:0.9em;">📋</span><span style="color:#F8FAFC;font-weight:600;font-size:0.85em;font-family:'Space Grotesk',sans-serif;">กระบวนการคิด</span></div>""", unsafe_allow_html=True)
    log_container = st.container(height=PIPELINE_LOG_HEIGHT, border=True)
    
    with st.expander("Logs"):
        raw_log_container = st.container(height=RAW_LOG_HEIGHT, border=False)

# --- 2. SETUP PLACEHOLDERS & UI UPDATERS ---
with log_container:
    log_placeholder = st.empty()
with raw_log_container:
    raw_placeholder = st.empty()

# Render chat statically in the container
with chat_container:
    chat_placeholder = st.empty()
    suggestions_placeholder = st.empty()

def update_chat_ui():
    html_parts = []
    for i, (role, message) in enumerate(st.session_state.chat_history):
        html_parts.append(get_chat_bubble_html(role, message))
        
    if st.session_state.pending_question:
        thinking_html = f'<div class="chat-row assistant"><div class="chat-avatar">{AI_AVATAR}</div><div class="chat-bubble" style="display:flex;align-items:center;gap:6px;min-height:48px;"><div class="dot chat-dot"></div><div class="dot chat-dot"></div><div class="dot chat-dot"></div></div></div>'
        html_parts.append(thinking_html)
        
    html_parts.append('<div id="chat-bottom" style="height:1px;"></div>')
    chat_placeholder.markdown("".join(html_parts), unsafe_allow_html=True)

update_chat_ui()

with chat_container:
    st_html(f"""<script>
        // timestamp: {time.time()}
        const parentWindow = window.parent;
        const parentDoc = parentWindow.document;
        
        // Inject global listener into parent context so it survives iframe destruction
        if (!parentWindow._hasReplyListener) {{
            const script = parentDoc.createElement('script');
            script.type = 'text/javascript';
            script.innerHTML = `
                window._hasReplyListener = true;
                document.addEventListener('click', function(e) {{
                    if (e.target && e.target.classList.contains('custom-reply-btn')) {{
                        const replyText = e.target.getAttribute('data-reply');
                        if (replyText) {{
                            const input = document.querySelector('textarea[data-testid="stChatInputTextArea"]');
                            if (input) {{
                                const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
                                nativeInputValueSetter.call(input, replyText);
                                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                
                                setTimeout(() => {{
                                    const btn = document.querySelector('div[data-testid="stChatInput"] button');
                                    if (btn) {{
                                        btn.click();
                                    }} else {{
                                        input.dispatchEvent(new KeyboardEvent('keydown', {{
                                            key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true
                                        }}));
                                    }}
                                }}, 100);
                            }}
                        }}
                    }}
                }});
            `;
            parentDoc.head.appendChild(script);
        }}
        
        const bottom = parentDoc.getElementById('chat-bottom');
        if (bottom) {{
            const chatContainer = bottom.closest('div[data-testid="stVerticalBlock"]');
            if (chatContainer) chatContainer.scrollTo({{top: chatContainer.scrollHeight, behavior: 'smooth'}});
        }}
        const focusInterval = setInterval(() => {{
            const chatInput = parentDoc.querySelector('textarea[data-testid="stChatInputTextArea"]');
            if (chatInput && !chatInput.disabled) {{
                chatInput.focus();
                clearInterval(focusInterval);
            }}
        }}, 100);
        setTimeout(() => clearInterval(focusInterval), 3000);
    </script>""", height=0)

def update_log_ui(logs_str, thinking=False):
    html_str = get_pipeline_logs_html(logs_str)
    
    if html_str:
        log_placeholder.markdown(html_str, unsafe_allow_html=True)
    else:
        if thinking:
            log_placeholder.markdown("""<div style="padding:20px;text-align:center;"><div style="color:#475569;font-size:0.85em;font-family:'Space Grotesk',sans-serif;">⏳ กำลังรอข้อมูลจากระบบ...</div></div>""", unsafe_allow_html=True)
        else:
            log_placeholder.markdown("""<div style="padding:20px;text-align:center;"><div style="color:#475569;font-size:0.85em;font-family:'Space Grotesk',sans-serif;">ยังไม่มี Log — พิมพ์คำถามเพื่อเริ่มต้น</div></div>""", unsafe_allow_html=True)
        
    if logs_str:
        raw_placeholder.code(logs_str, language=None)
    else:
        raw_placeholder.info("No logs available.")

class StreamlitLogRedirector:
    def __init__(self):
        self.buffer = ""
    def write(self, text):
        self.buffer += text
        if "\n" in text:
            update_log_ui(self.buffer)
    def flush(self):
        pass
    def getvalue(self):
        return self.buffer

# Initial UI render
if st.session_state.pending_question:
    # Clear logs when a new question is submitted so we see the loading state
    st.session_state.last_logs = ""
    update_log_ui("", thinking=True)
else:
    update_log_ui(st.session_state.last_logs, thinking=False)

# --- 3. PROCESS PENDING QUESTION ---
if st.session_state.pending_question:
    question = st.session_state.pending_question
    redirector = StreamlitLogRedirector()
    
    start_time = time.time()
    
    with contextlib.redirect_stdout(redirector):
        if UI_TEST_MODE:
            time.sleep(2.0)
            print("[route_node] Category: ประกันรถยนต์")
            time.sleep(2.0)
            print("[search_node] ผ่านการตรวจ: เอกสารจำลอง 1, 2")
            time.sleep(2.0)
            print("[generate_node] Model: gpt-4o-mini (mock)")
            time.sleep(2.0)
            print("[hallucination_check_node] ✅ grounded")
            time.sleep(2.0)
            answer = (
                "นี่คือข้อความจำลองจาก UI_TEST_MODE ครับ! ถ้าพร้อมจะทดสอบระบบจริง "
                "ให้แก้ UI_TEST_MODE = False ที่บรรทัดที่ 8 ของ app.py นะครับ"
            )
        else:
            answer = answer_question(
                question,
                app,
                st.session_state.answer_cache,
                st.session_state.conversation,
            )
            
    # บังคับให้ใช้เวลาคิดขั้นต่ำ 2 วินาที
    elapsed_time = time.time() - start_time
    if elapsed_time < 2.0:
        time.sleep(2.0 - elapsed_time)
            
    st.session_state.last_logs = redirector.getvalue()
    st.session_state.chat_history.append(("assistant", answer))
    st.session_state.pending_question = None
    
    # Update UI with the final answer and logs
    update_log_ui(st.session_state.last_logs)
    update_chat_ui()
    st.rerun()
