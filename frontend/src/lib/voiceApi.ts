import { ApiError } from "./api";
import { getToken } from "./session";
import type {
  AgentTurnResponse,
  AnswerSource,
  ConversationMessage,
  TranscribeResponse,
} from "./types";

const BASE_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

async function call(path: string, init: RequestInit): Promise<Response> {
  const headers = new Headers(init.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let response: Response;
  try {
    response = await fetch(`${BASE_URL}/api${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, "network_error", "Cannot reach the server. Please try again.");
  }

  if (!response.ok) {
    let code = "http_error";
    let message = `Request failed (${response.status}).`;
    let details: unknown;
    try {
      const data = await response.json();
      if (data?.error) {
        code = data.error.code ?? code;
        message = data.error.message ?? message;
        details = data.error.details;
      }
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(response.status, code, message, details);
  }
  return response;
}

/** Send a WAV recording. `fieldId` is the field being answered (emails and PAN
 *  are recognised in English). Always resolves unless the server is unreachable. */
export async function transcribeAudio(wav: Blob, fieldId: string | null): Promise<TranscribeResponse> {
  const form = new FormData();
  form.append("audio", wav, "recording.wav");
  if (fieldId) form.append("field_id", fieldId);
  const response = await call("/voice/transcribe", { method: "POST", body: form });
  return (await response.json()) as TranscribeResponse;
}

/** Spoken audio (mp3) for a reply. Throws ApiError with details.fallback on failure. */
export async function speak(text: string): Promise<Blob> {
  const response = await call("/voice/speak", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  return await response.blob();
}

export async function agentTurn(text: string, source: AnswerSource): Promise<AgentTurnResponse> {
  const response = await call("/conversation/turn", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, source }),
  });
  return (await response.json()) as AgentTurnResponse;
}

export async function getMessages(): Promise<ConversationMessage[]> {
  const response = await call("/conversation/messages", { method: "GET" });
  return ((await response.json()) as { messages: ConversationMessage[] }).messages;
}