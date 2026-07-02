import type { ChatMessage } from "../types";
import aiAvatar from "../assets/ai_avatar.jpg";

interface Props {
  message: ChatMessage;
  onOptionClick: (value: string) => void;
  disabled: boolean;
}

export default function ChatBubble({ message, onOptionClick, disabled }: Props) {
  const isUser = message.role === "user";

  return (
    <div className={`chat-row ${isUser ? "user" : "assistant"}`}>
      <div className="chat-avatar">
        {isUser ? (
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
            <circle cx="12" cy="7" r="4"></circle>
          </svg>
        ) : (
          <img src={aiAvatar} alt="AI" style={{ width: "100%", height: "100%", objectFit: "cover", borderRadius: "50%" }} />
        )}
      </div>
      <div>
        <div className="chat-bubble">{message.text}</div>
        {message.options && message.options.length > 0 && (
          <div className="reply-options">
            {message.options.map((opt) => (
              <button
                key={opt.value}
                type="button"
                className="custom-reply-btn"
                disabled={disabled}
                onClick={() => onOptionClick(opt.value)}
              >
                {opt.label}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
