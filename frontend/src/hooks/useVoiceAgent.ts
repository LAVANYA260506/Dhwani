"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError } from "../lib/api";
import { agentTurn, getMessages, speak, transcribeAudio } from "../lib/voiceApi";
import { blobToWav } from "../lib/wav";
import type { AgentTurnResponse, AnswerSource, Language } from "../lib/types";

export type VoiceState = "idle" | "listening" | "processing" | "speaking";

export interface ChatMessage {
  id: string;
  role: "applicant" | "assistant" | "notice";
  text: string;
  channel?: AnswerSource;
}

interface Options {
  enabled: boolean; // true once an application exists
  language: Language;
  currentField: string | null;
  onTurn?: (response: AgentTurnResponse) => void;
}

const MAX_RECORDING_MS = 25000; // Gnani accepts up to 30 seconds
const MIN_RECORDING_MS = 400;

const NOTICES = {
  mic_denied: {
    en: "I can't use the microphone. Allow microphone access in your browser, or type your answer.",
    kn: "ಮೈಕ್ರೊಫೋನ್ ಬಳಸಲು ಸಾಧ್ಯವಿಲ್ಲ. ಬ್ರೌಸರ್‌ನಲ್ಲಿ ಮೈಕ್ರೊಫೋನ್ ಅನುಮತಿಸಿ, ಅಥವಾ ಟೈಪ್ ಮಾಡಿ.",
  },
  too_short: {
    en: "That was too short. Hold on a little longer and speak.",
    kn: "ತುಂಬಾ ಚಿಕ್ಕದಾಗಿತ್ತು. ಸ್ವಲ್ಪ ಹೊತ್ತು ಮಾತನಾಡಿ.",
  },
  failed: {
    en: "Something went wrong. Please try again or type your answer.",
    kn: "ಏನೋ ತಪ್ಪಾಯಿತು. ಮತ್ತೊಮ್ಮೆ ಪ್ರಯತ್ನಿಸಿ ಅಥವಾ ಟೈಪ್ ಮಾಡಿ.",
  },
} as const;

export function useVoiceAgent({ enabled, language, currentField, onTurn }: Options) {
  const [state, setState] = useState<VoiceState>("idle");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [voiceAvailable, setVoiceAvailable] = useState(true);
  const [speakReplies, setSpeakReplies] = useState(true);
  const [lastTurn, setLastTurn] = useState<AgentTurnResponse | null>(null);

  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const startedAtRef = useRef(0);
  const stopTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioUrlRef = useRef<string | null>(null);
  const counterRef = useRef(0);

  // Latest values for callbacks that outlive a render
  const live = useRef({ language, currentField, onTurn, speakReplies, voiceAvailable });
  live.current = { language, currentField, onTurn, speakReplies, voiceAvailable };

  const addMessage = useCallback((role: ChatMessage["role"], text: string, channel?: AnswerSource) => {
    counterRef.current += 1;
    setMessages((prev) => [...prev, { id: `m${counterRef.current}`, role, text, channel }]);
  }, []);

  const notice = useCallback(
    (key: keyof typeof NOTICES, textOverride?: string) =>
      addMessage("notice", textOverride ?? NOTICES[key][live.current.language]),
    [addMessage]
  );

  // ---- Resume: load the earlier conversation ----
  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    getMessages()
      .then((history) => {
        if (cancelled) return;
        setMessages(
          history.map((m) => ({
            id: `h${m.id}`,
            role: m.role === "applicant" ? "applicant" : "assistant",
            text: m.content,
            channel: m.channel === "voice" ? "voice" : "text",
          }))
        );
      })
      .catch(() => {
        /* a missing history is not an error */
      });
    return () => {
      cancelled = true;
    };
  }, [enabled]);

  // ---- Playback ----
  const stopSpeaking = useCallback(() => {
    const audio = audioRef.current;
    if (audio) {
      audio.onended = null;
      audio.pause();
      audioRef.current = null;
    }
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = null;
    }
    setState((current) => (current === "speaking" ? "idle" : current));
  }, []);

  const playReply = useCallback(
    async (speech: string) => {
      try {
        const blob = await speak(speech);
        const url = URL.createObjectURL(blob);
        audioUrlRef.current = url;
        const audio = new Audio(url);
        audioRef.current = audio;
        audio.onended = () => stopSpeaking();
        setState("speaking");
        await audio.play();
      } catch (err) {
        stopSpeaking();
        setState("idle");
        if (err instanceof ApiError) {
          const fallback = (err.details as { fallback?: string } | undefined)?.fallback;
          if (fallback === "type") setVoiceAvailable(false);
          notice("failed", err.message);
        }
        // A blocked autoplay or a decode problem: the text reply is already shown
      }
    },
    [notice, stopSpeaking]
  );

  // ---- One conversational turn ----
  const runTurn = useCallback(
    async (text: string, source: AnswerSource) => {
      setState("processing");
      try {
        const response = await agentTurn(text, source);
        setLastTurn(response);
        addMessage("assistant", response.reply);
        live.current.onTurn?.(response);
        if (live.current.speakReplies && live.current.voiceAvailable) {
          await playReply(response.speech);
        } else {
          setState("idle");
        }
      } catch (err) {
        setState("idle");
        notice("failed", err instanceof Error ? err.message : undefined);
      }
    },
    [addMessage, notice, playReply]
  );

  /** Typed answers (the fallback). */
  const sendText = useCallback(
    async (text: string) => {
      const clean = text.trim();
      if (!clean || state === "processing") return;
      stopSpeaking();
      addMessage("applicant", clean, "text");
      await runTurn(clean, "text");
    },
    [addMessage, runTurn, state, stopSpeaking]
  );

  // ---- Recording ----
  const handleRecording = useCallback(
    async (blob: Blob, durationMs: number) => {
      if (durationMs < MIN_RECORDING_MS || blob.size === 0) {
        setState("idle");
        notice("too_short");
        return;
      }
      setState("processing");
      try {
        const wav = await blobToWav(blob);
        const result = await transcribeAudio(wav, live.current.currentField);
        if (!result.ok) {
          setState("idle");
          if (result.fallback === "type") setVoiceAvailable(false);
          notice("failed", result.message ?? undefined);
          return;
        }
        addMessage("applicant", result.text, "voice");
        await runTurn(result.normalized || result.text, "voice");
      } catch (err) {
        setState("idle");
        notice("failed", err instanceof Error ? err.message : undefined);
      }
    },
    [addMessage, notice, runTurn]
  );

  const releaseMicrophone = useCallback(() => {
    if (stopTimerRef.current) clearTimeout(stopTimerRef.current);
    stopTimerRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  }, []);

  const stopListening = useCallback(() => {
    const recorder = recorderRef.current;
    if (recorder && recorder.state !== "inactive") recorder.stop();
  }, []);

  /** Start recording. If the assistant is speaking, it stops (barge-in). */
  const startListening = useCallback(async () => {
    if (state === "processing" || state === "listening") return;
    stopSpeaking();

    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      notice("mic_denied");
      return;
    }

    streamRef.current = stream;
    chunksRef.current = [];
    const recorder = new MediaRecorder(stream);
    recorderRef.current = recorder;
    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) chunksRef.current.push(event.data);
    };
    recorder.onstop = () => {
      const duration = Date.now() - startedAtRef.current;
      const blob = new Blob(chunksRef.current, { type: recorder.mimeType });
      releaseMicrophone();
      recorderRef.current = null;
      void handleRecording(blob, duration);
    };

    startedAtRef.current = Date.now();
    recorder.start();
    setState("listening");
    stopTimerRef.current = setTimeout(stopListening, MAX_RECORDING_MS);
  }, [handleRecording, notice, releaseMicrophone, state, stopListening, stopSpeaking]);

  // ---- Clean up when the component goes away ----
  useEffect(
    () => () => {
      const recorder = recorderRef.current;
      if (recorder && recorder.state !== "inactive") {
        recorder.onstop = null;
        recorder.stop();
      }
      releaseMicrophone();
      audioRef.current?.pause();
      if (audioUrlRef.current) URL.revokeObjectURL(audioUrlRef.current);
    },
    [releaseMicrophone]
  );

  return {
    state,
    messages,
    lastTurn,
    voiceAvailable,
    speakReplies,
    setSpeakReplies,
    startListening,
    stopListening,
    stopSpeaking,
    sendText,
  };
}