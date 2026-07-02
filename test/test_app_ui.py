from streamlit.testing.v1 import AppTest
from pathlib import Path


def walk_tree(node):
    yield node
    for child in getattr(node, "children", {}).values():
        yield from walk_tree(child)


def test_chat_and_log_panels_fit_the_viewport_and_chat_roles_have_distinct_alignment():
    app = AppTest.from_file("app.py").run(timeout=20)

    heights = [
        node.proto.vertical.height
        for node in walk_tree(app._tree)
        if getattr(node, "type", None) == "vertical"
        and node.proto.vertical.height
    ]

    assert not app.exception
    assert heights == [440, 320, 100]

    rendered_css = "\n".join(
        markdown.value
        for markdown in app.markdown
        if "<style>" in markdown.value
    )
    rendered_markup = "\n".join(markdown.value for markdown in app.markdown)
    assert 'class="chat-row assistant"' in rendered_markup
    assert ".chat-row.user {" in rendered_css
    assert "flex-direction: row-reverse;" in rendered_css
    assert ".chat-bubble {" in rendered_css
    assert "overflow-wrap: anywhere;" in rendered_css
    assert "white-space: pre-wrap;" in rendered_css
    assert "padding: 12px 14px;" in rendered_css

def test_first_processing_state_is_rendered_inside_chat_panel():
    source = Path("app.py").read_text(encoding="utf-8")

    chat_container_position = source.index("with chat_container:")
    thinking_position = source.index('class="chat-thinking"')
    chat_input_position = source.index("user_question = st.chat_input")

    assert chat_container_position < thinking_position < chat_input_position
    assert "pending_question" in source
    assert "live_status_area" not in source
    assert 'st.spinner("Processing...")' not in source
    assert source.count("st.rerun()") == 0
    assert "on_submit=queue_question" in source

def test_ui_assets_are_separate_from_app():
    app_source = Path("app.py").read_text(encoding="utf-8")
    component_source = Path("ui/components.py").read_text(encoding="utf-8")
    stylesheet = Path("ui/styles.css").read_text(encoding="utf-8")

    assert "def render_chat_bubble" not in app_source
    assert "def render_pipeline_logs" not in app_source
    assert "<style>" not in app_source
    assert "def render_chat_bubble" in component_source
    assert "def render_pipeline_logs" in component_source
    assert "def load_styles" in component_source
    assert ".chat-bubble" in stylesheet
    assert ".chat-thinking" in stylesheet
    assert '[data-stale="true"]' in stylesheet

def test_streamlit_fast_reruns_are_disabled():
    config = Path(".streamlit/config.toml").read_text(encoding="utf-8")

    assert "[runner]" in config
    assert "fastReruns = false" in config



