import type { LogStep } from "../types";
import { dotColorForType } from "../parseLogLine";

interface Props {
  steps: LogStep[];
  thinking: boolean;
  rawLogs: string;
}

export default function LogPanel({ steps, thinking, rawLogs }: Props) {
  let stepNumber = 0;

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
            const nextStep = steps[i + 1];
            // เส้นเชื่อมลงล่างวาดต่อเฉพาะตอนตัวถัดไปเป็น step ปกติ (ไม่ใช่ตัวสุดท้าย
            // และไม่ใช่เส้นแบ่งคำถามใหม่) กันเส้นค้างลอยๆ ตรงรอยต่อระหว่างคำถาม
            const isLast = !nextStep || nextStep.isTurnMarker;

            if (step.isTurnMarker) {
              stepNumber = 0; // เริ่มนับ Step ใหม่ทุกครั้งที่ขึ้นคำถามใหม่ ให้อ่านง่ายเหมือนเดิม
              return (
                <div className="log-turn-marker" key={i}>
                  <span className="log-turn-marker-icon">{step.icon}</span>
                  <span className="log-turn-marker-text">{step.detail}</span>
                </div>
              );
            }

            stepNumber += 1;
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
                      Step {stepNumber}
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
