import type { LogStep } from "../types";
import { dotColorForType } from "../parseLogLine";

interface Props {
  steps: LogStep[];
  thinking: boolean;
  rawLogs: string;
}

export default function LogPanel({ steps, thinking, rawLogs }: Props) {
  return (
    <>
      <div className="panel-header">
        <span>📋</span>
        <span className="panel-title">กระบวนการคิด</span>
      </div>
      <div className="log-container">
        {steps.length === 0 ? (
          <div className="log-empty">
            {thinking ? "⏳ กำลังรอข้อมูลจากระบบ..." : "ยังไม่มี Log — พิมพ์คำถามเพื่อเริ่มต้น"}
          </div>
        ) : (
          steps.map((step, i) => {
            const isLast = i === steps.length - 1;
            const color = dotColorForType(step.type);
            return (
              <div className="log-step" key={i}>
                <div className="log-step-rail">
                  <div className="log-step-dot" style={{ background: `${color}26`, borderColor: color, boxShadow: `0 0 6px ${color}66` }} />
                  {!isLast && <div className="log-step-line" style={{ background: color }} />}
                </div>
                <div className="log-step-card">
                  <div className="log-step-row">
                    <span className="log-step-title">
                      {step.icon} {step.title}
                    </span>
                    <span className="log-step-badge" style={{ color, background: `${color}1A` }}>
                      Step {i + 1}
                    </span>
                  </div>
                  <div className="log-step-detail">{step.detail}</div>
                </div>
              </div>
            );
          })
        )}
      </div>
      <details className="raw-logs">
        <summary>Logs</summary>
        <pre>{rawLogs || "No logs available."}</pre>
      </details>
    </>
  );
}
