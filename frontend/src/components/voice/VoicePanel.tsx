"use client";

import { useEffect, useRef, useState } from "react";

import type { useVoiceAgent } from "@/hooks/useVoiceAgent";
import type { Language } from "@/lib/types";

type Voice = ReturnType<typeof useVoiceAgent>;

const TEXT = {
  title: { en: "Dhwani, your voice assistant", kn: "ಧ್ವನಿ, ನಿಮ್ಮ ಧ್ವನಿ ಸಹಾಯಕ" },
  idle: { en: "Tap the microphone and speak", kn: "ಮೈಕ್ ಒತ್ತಿ ಮಾತನಾಡಿ" },
  listening: { en: "Listening... tap to send", kn: "ಕೇಳುತ್ತಿದ್ದೇನೆ... ಕಳುಹಿಸಲು ಒತ್ತಿ" },
  processing: { en: "Thinking...", kn: "ಯೋಚಿಸುತ್ತಿದ್ದೇನೆ..." },
  speaking: { en: "Speaking... tap to interrupt", kn: "ಮಾತನಾಡುತ್ತಿದ್ದೇನೆ... ನಿಲ್ಲಿಸಲು ಒತ್ತಿ" },
  empty: {
    en: "Say something like: “My name is Lavanya, born 14 May 2003.” You can also ask what a field means.",
    kn: "ಹೀಗೆ ಹೇಳಿ: “ನನ್ನ ಹೆಸರು ಲಕ್ಷ್ಮಿ, ಹುಟ್ಟಿದ ದಿನಾಂಕ 14 ಮೇ 2003.” ಯಾವುದಾದರೂ ಕ್ಷೇತ್ರದ ಅರ್ಥವನ್ನೂ ಕೇಳಬಹುದು.",
  },
  placeholder: { en: "Or type your answer here", kn: "ಅಥವಾ ಇಲ್ಲಿ ಟೈಪ್ ಮಾಡಿ" },
  send: { en: "Send", kn: "ಕಳುಹಿಸಿ" },
  yes: { en: "Yes, correct", kn: "ಹೌದು, ಸರಿ" },
  no: { en: "No", kn: "ಇಲ್ಲ" },
  confirmAsk: { en: "Is this correct?", kn: "ಇದು ಸರಿಯೇ?" },
  speakReplies: { en: "Speak replies aloud", kn: "ಉತ್ತರಗಳನ್ನು ಧ್ವನಿಯಲ್ಲಿ ಹೇಳು" },
  noVoice: {
    en: "Voice is not available right now. You can keep going by typing.",
    kn: "ಧ್ವನಿ ಸೇವೆ ಈಗ ಲಭ್ಯವಿಲ್ಲ. ಟೈಪ್ ಮಾಡಿ ಮುಂದುವರಿಸಬಹುದು.",
  },
  noMic: {
    en: "This browser cannot record audio. Please type your answers.",
    kn: "ಈ ಬ್ರೌಸರ್ ಆಡಿಯೋ ರೆಕಾರ್ಡ್ ಮಾಡಲು ಸಾಧ್ಯವಿಲ್ಲ. ದಯವಿಟ್ಟು ಟೈಪ್ ಮಾಡಿ.",
  },
  localhostHint: {
    en: "Open this page at http://localhost:3000 (not an IP address).",
    kn: "http://localhost:3000 ನಲ್ಲಿ ಪುಟ ತೆರೆಯಿರಿ.",
  },
};

const STATE_STYLE: Record<Voice["state"], string> = {
  idle: "bg-accent hover:bg-accent-dark",
  listening: "bg-danger animate-pulse",
  processing: "bg-muted",
  speaking: "bg-brand",
};

function MicIcon() {
  return (
    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <rect x="9" y="3" width="6" height="11" rx="3" fill="currentColor" />
      <path
        d="M5 11a7 7 0 0 0 14 0M12 18v3"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

export default function VoicePanel({ voice, language }: { voice: Voice; language: Language }) {
  const [draft, setDraft] = useState("");
  const [micSupported, setMicSupported] = useState(true);
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setMicSupported(typeof navigator !== "undefined" && !!navigator.mediaDevices?.getUserMedia);
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [voice.messages.length]);

  const { state } = voice;
  const busy = state === "processing";
  const pending = voice.lastTurn?.pending_confirmation ?? [];
  const canUseMic = micSupported && voice.voiceAvailable;

  const onMicClick = () => {
    if (state === "listening") voice.stopListening();
    else void voice.startListening();
  };

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!draft.trim()) return;
    void voice.sendText(draft);
    setDraft("");
  };

  return (
    <section aria-label={TEXT.title[language]} className="card flex h-full flex-col">
      <header className="border-b border-line px-4 py-3">
        <h2 className="!text-lg">{TEXT.title[language]}</h2>
      </header>

      <div
        className="min-h-[14rem] flex-1 space-y-3 overflow-y-auto px-4 py-3 lg:max-h-[26rem]"
        aria-live="polite"
      >
        {voice.messages.length === 0 && (
          <p className="text-sm text-muted">{TEXT.empty[language]}</p>
        )}
        {voice.messages.map((m) => (
          <div
            key={m.id}
            className={m.role === "applicant" ? "flex justify-end" : "flex justify-start"}
          >
            <p
              className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
                m.role === "applicant"
                  ? "bg-brand text-white"
                  : m.role === "notice"
                    ? "border border-warning bg-white text-body"
                    : "bg-tint text-strong"
              }`}
            >
              {m.text}
            </p>
          </div>
        ))}
        <div ref={endRef} />
      </div>

      {pending.length > 0 && !busy && (
        <div className="mx-4 mb-3 rounded-md border border-accent bg-tint-light p-3">
          <p className="mb-2 text-sm font-semibold text-strong">{TEXT.confirmAsk[language]}</p>
          <div className="flex gap-2">
            <button
              type="button"
              className="btn btn-primary !py-1.5"
              onClick={() => void voice.sendText(language === "kn" ? "ಹೌದು" : "yes")}
            >
              {TEXT.yes[language]}
            </button>
            <button
              type="button"
              className="btn btn-secondary !py-1.5"
              onClick={() => void voice.sendText(language === "kn" ? "ಇಲ್ಲ" : "no")}
            >
              {TEXT.no[language]}
            </button>
          </div>
        </div>
      )}

      <div className="border-t border-line px-4 py-4">
        {/* The microphone button is always shown; it is greyed out, with the
            reason underneath, when recording is not possible. */}
        <div className="flex flex-col items-center gap-2">
          <button
            type="button"
            onClick={onMicClick}
            disabled={busy || !canUseMic}
            aria-label={TEXT[state][language]}
            className={`flex h-16 w-16 items-center justify-center rounded-full text-white shadow-card disabled:cursor-not-allowed disabled:opacity-50 ${
              canUseMic ? STATE_STYLE[state] : "bg-muted"
            }`}
          >
            <MicIcon />
          </button>
          <p className="text-center text-sm text-muted">
            {canUseMic
              ? TEXT[state][language]
              : micSupported
                ? TEXT.noVoice[language]
                : TEXT.noMic[language]}
          </p>
          {!micSupported && (
            <p className="text-center text-xs text-warning">{TEXT.localhostHint[language]}</p>
          )}
        </div>

        <form onSubmit={submit} className="mt-4 flex gap-2">
          <input
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder={TEXT.placeholder[language]}
            aria-label={TEXT.placeholder[language]}
            className="min-w-0 flex-1 rounded border border-line bg-white px-3 py-2 text-strong"
          />
          <button
            type="submit"
            className="btn btn-primary !py-2"
            disabled={busy || !draft.trim()}
          >
            {TEXT.send[language]}
          </button>
        </form>

        <label className="mt-3 flex items-center gap-2 text-xs text-muted">
          <input
            type="checkbox"
            checked={voice.speakReplies}
            onChange={(event) => voice.setSpeakReplies(event.target.checked)}
          />
          {TEXT.speakReplies[language]}
        </label>
      </div>
    </section>
  );
}