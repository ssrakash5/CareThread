"use client";

import { useEffect, useRef, useState, useTransition } from "react";
import { Send } from "lucide-react";

interface ChatMsg {
  message_id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export default function ChatPanel({
  fetchHistory, ask, label, placeholder, emptyHint, accentClass = "bg-purple-600 hover:bg-purple-700", bordered = true,
}: {
  fetchHistory: () => Promise<ChatMsg[]>;
  ask: (question: string) => Promise<unknown>;
  label?: string;
  placeholder: string;
  emptyHint: string;
  accentClass?: string;
  bordered?: boolean;
}) {
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [question, setQuestion] = useState("");
  const [loaded, setLoaded] = useState(false);
  const [pending, startTransition] = useTransition();
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchHistory().then((msgs) => {
      setMessages(msgs);
      setLoaded(true);
    });
    // fetchHistory/ask are recreated per render by the caller; re-run only when the underlying id changes via `label`+`placeholder` identity is not reliable, so callers should key this component by id instead.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages]);

  function send() {
    const q = question.trim();
    if (!q) return;
    setQuestion("");
    setMessages((prev) => [
      ...prev,
      { message_id: `pending-${Date.now()}`, role: "user", content: q, created_at: new Date().toISOString() },
    ]);
    startTransition(async () => {
      await ask(q);
      const history = await fetchHistory();
      setMessages(history);
    });
  }

  return (
    <div className={bordered ? "mt-4 border-t border-slate-100 pt-3" : "mt-3"}>
      {label && <div className="text-xs font-medium text-slate-500 mb-2">{label}</div>}
      {loaded && messages.length === 0 && (
        <p className="text-xs text-slate-400 mb-2">{emptyHint}</p>
      )}
      {messages.length > 0 && (
        <div ref={scrollRef} className="max-h-56 overflow-y-auto space-y-2 mb-2 pr-1">
          {messages.map((m) => (
            <div
              key={m.message_id}
              className={`text-xs rounded-lg px-3 py-2 whitespace-pre-wrap ${
                m.role === "user" ? "bg-teal-50 text-slate-800 ml-6" : "bg-slate-50 text-slate-700 mr-2"
              }`}
            >
              {m.content}
            </div>
          ))}
          {pending && <div className="text-xs text-slate-400 px-3">Thinking…</div>}
        </div>
      )}
      <div className="flex gap-2">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !pending && send()}
          placeholder={placeholder}
          className="flex-1 border border-slate-300 rounded-md px-2.5 py-1.5 text-xs"
        />
        <button
          disabled={pending || !question.trim()}
          onClick={send}
          className={`rounded-md text-white px-2.5 py-1.5 disabled:opacity-40 ${accentClass}`}
        >
          <Send size={13} />
        </button>
      </div>
    </div>
  );
}
