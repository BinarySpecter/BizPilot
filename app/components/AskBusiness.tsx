"use client";

import { useRef, useState } from "react";
import type { Analysis } from "../lib/types";
import { chatWithBusiness } from "../lib/api";
import { ArrowRightIcon } from "./icons";

type Msg = {
  role: "user" | "assistant";
  content: string;
  meta?: { mode?: "llm" | "deterministic"; related_view?: string };
};

const VIEW_LABEL: Record<string, string> = {
  overview: "Overview",
  signals: "Signals",
  insights: "Insights",
  actions: "Actions",
  simulate: "Simulation",
  ask: "Ask Business",
};

const SUGGESTIONS = [
  "Why did sales fall last week?",
  "What should I restock first?",
  "Which products are slowing down?",
  "What happens if demand rises 20%?",
  "Are there any unusual sales patterns?",
];

// Minimal markdown-lite for model answers (**bold**, line breaks, "- " bullets).
function renderAnswer(text: string) {
  const lines = text.split("\n");
  return lines.map((line, i) => {
    const trimmed = line.trim();
    if (!trimmed) return <br key={i} />;
    if (/^[-•]\s/.test(trimmed)) {
      return (
        <div className="rb-item" key={i}>
          <span className="rb-dot" />
          {inline(trimmed.replace(/^[-•]\s/, ""))}
        </div>
      );
    }
    return <p key={i} className="rb-p">{inline(trimmed)}</p>;
  });
}

function inline(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) =>
    part.startsWith("**") && part.endsWith("**") ? (
      <strong key={i}>{part.slice(2, -2)}</strong>
    ) : (
      <span key={i}>{part}</span>
    ),
  );
}

export default function AskBusiness({ analysis }: { analysis: Analysis }) {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const send = async (question?: string) => {
    const q = (question ?? input).trim();
    if (!q || busy) return;
    setInput("");
    setError(null);
    setBusy(true);
    const next = [...messages, { role: "user", content: q } as Msg];
    setMessages(next);
    try {
      const res = await chatWithBusiness(analysis, q, next);
      if (res.ok && res.answer) {
        setMessages([
          ...next,
          {
            role: "assistant",
            content: res.answer,
            meta: { mode: res.mode, related_view: res.related_view },
          },
        ]);
      } else {
        setMessages(next);
        setError(
          "We couldn't produce an answer for that question right now — try one of the suggested questions.",
        );
      }
    } catch (e: any) {
      setError(
        e?.message && /chat/i.test(String(e.message)) && !/api/i.test(String(e.message))
          ? "We couldn't reach the analytics service — the dashboard still works."
          : "That question couldn't be answered right now — try one of the suggested questions.",
      );
      setMessages(next);
    } finally {
      setBusy(false);
      setTimeout(() => listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" }), 50);
    }
  };

  return (
    <div className="well ask">
      <div className="ask-body" ref={listRef}>
        {messages.length === 0 && (
          <div className="ask-empty">
            <p className="ask-empty-t">Ask about restocking, demand, or unusual patterns.</p>
            <p className="ask-empty-s muted small">
              Answers are grounded in the analytics computed from your data.
            </p>
            <ul className="sugg">
              {SUGGESTIONS.map((s) => (
                <li key={s}>
                  <button type="button" className="sugg-btn" disabled={busy} onClick={() => send(s)}>
                    <span>{s}</span>
                    <ArrowRightIcon size={13} />
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={`bubble ${m.role === "user" ? "bubble-user" : "bubble-bot"}`}>
            {m.role === "assistant" ? (
              <>
                <div className="rb-content">{renderAnswer(m.content)}</div>
                {m.meta && (
                  <div className="bubble-meta">
                    <span className="bm-row">
                      {m.meta.mode === "deterministic" && (
                        <span className="bm-note mono">evidence-based answer · grounded in computed analytics</span>
                      )}
                    </span>
                    {m.meta.related_view && (
                      <a className="bm-link" href={`#/${m.meta.related_view}`}>
                        Open {VIEW_LABEL[m.meta.related_view] ?? "view"}
                        <ArrowRightIcon size={12} />
                      </a>
                    )}
                  </div>
                )}
              </>
            ) : (
              m.content
            )}
          </div>
        ))}

        {busy && (
          <div className="bubble bubble-bot">
            <span className="typing"><i /><i /><i /></span>
          </div>
        )}

        {error && <div className="alert alert-error">{error}</div>}
      </div>

      <form className="ask-form" onSubmit={(e) => { e.preventDefault(); send(); }}>
        <input
          className="input ask-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="What should I restock first?"
          aria-label="Question for your business data"
        />
        <button type="submit" className="btn btn-primary" disabled={busy || !input.trim()}>
          Ask
        </button>
      </form>

      <style jsx>{`
        .ask {
          overflow: hidden;
        }
        .ask-body {
          overflow-y: auto;
          max-height: 520px;
          padding: 22px 26px 16px;
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .ask-empty {
          margin: auto;
          max-width: 520px;
          padding: 26px 0;
        }
        .ask-empty-t {
          font-size: 17px;
          font-weight: 620;
          letter-spacing: -0.015em;
        }
        .ask-empty-s {
          margin-top: 6px;
        }
        .sugg {
          list-style: none;
          margin: 20px 0 0;
          padding: 0;
          border-top: 1px solid var(--border);
        }
        .sugg-btn {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          width: 100%;
          border: 0;
          border-bottom: 1px solid var(--border);
          background: transparent;
          padding: 12px 6px;
          font-size: 13.5px;
          color: var(--ink-2);
          cursor: pointer;
          text-align: left;
          transition: color 0.15s ease, background 0.15s ease;
        }
        .sugg-btn svg {
          opacity: 0;
          transform: translateX(-4px);
          transition: opacity 0.15s ease, transform 0.15s ease;
        }
        .sugg-btn:hover:not(:disabled) {
          color: var(--blue-ink);
          background: var(--blue-soft);
        }
        .sugg-btn:hover:not(:disabled) svg {
          opacity: 1;
          transform: translateX(0);
        }
        .sugg-btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }
        .bubble {
          max-width: 72%;
          padding: 10px 14px;
          font-size: 13.8px;
          line-height: 1.55;
        }
        .bubble-user {
          align-self: flex-end;
          background: var(--blue);
          color: #fff;
          border-radius: 8px 8px 2px 8px;
        }
        .bubble-bot {
          align-self: stretch;
          max-width: 100%;
          background: var(--surface-2);
          border: 1px solid var(--border);
          border-left: 3px solid var(--blue);
          border-radius: 2px 8px 8px 8px;
          color: var(--ink);
        }
        .bubble-bot strong {
          color: var(--blue-ink);
          font-weight: 700;
          font-variant-numeric: tabular-nums;
        }
        .bubble-meta {
          margin-top: 10px;
          padding-top: 8px;
          border-top: 1px solid var(--border);
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          flex-wrap: wrap;
        }
        .bm-note {
          font-size: 10.5px;
          letter-spacing: 0.04em;
          color: var(--ink-4);
        }
        .bm-link {
          display: inline-flex;
          align-items: center;
          gap: 5px;
          font-size: 12px;
          font-weight: 650;
          color: var(--blue-ink);
          text-decoration: none;
          white-space: nowrap;
        }
        .bm-link:hover {
          text-decoration: underline;
          text-underline-offset: 2px;
        }
        .rb-p {
          margin: 0 0 6px;
        }
        .rb-item {
          display: flex;
          gap: 9px;
          margin: 3px 0;
        }
        .rb-dot {
          width: 5px;
          height: 5px;
          border-radius: 50%;
          background: var(--blue);
          margin-top: 8px;
          flex: none;
        }
        .typing {
          display: inline-flex;
          gap: 4px;
          padding: 4px 0;
        }
        .typing i {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: var(--ink-4);
          animation: blink 1.2s infinite;
        }
        .typing i:nth-child(2) { animation-delay: 0.2s; }
        .typing i:nth-child(3) { animation-delay: 0.4s; }
        @keyframes blink {
          0%, 80%, 100% { opacity: 0.3; }
          40% { opacity: 1; }
        }
        .ask-form {
          display: flex;
          gap: 10px;
          padding: 14px 26px 18px;
          border-top: 1px solid var(--border);
        }
        .ask-input {
          flex: 1;
          border-radius: var(--radius-sm);
        }
        @media (max-width: 640px) {
          .ask-body,
          .ask-form {
            padding-left: 18px;
            padding-right: 18px;
          }
        }
      `}</style>
    </div>
  );
}