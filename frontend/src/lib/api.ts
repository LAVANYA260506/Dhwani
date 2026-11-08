import { getToken } from "./session";
import type {
  AnswerSource,
  ApplicationCreated,
  ApplicationRead,
  EventList,
  FieldUpdateResult,
  FieldValue,
  Language,
} from "./types";

const BASE_URL = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
).replace(/\/$/, "");

/** Error with the backend's {"error": {code, message, details}} shape. */
export class ApiError extends Error {
  status: number;
  code: string;
  details?: unknown;

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

async function request<T>(
  path: string,
  options: { method?: string; body?: unknown; auth?: boolean } = {}
): Promise<T> {
  const { method = "GET", body, auth = true } = options;
  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (auth) {
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetch(`${BASE_URL}/api${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
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

  return (await response.json()) as T;
}

export const api = {
  createApplication: (language: Language, consentGiven: boolean) =>
    request<ApplicationCreated>("/applications", {
      method: "POST",
      auth: false,
      body: { language, consent_given: consentGiven },
    }),

  getApplication: () => request<ApplicationRead>("/applications/me"),

  resumeApplication: () => request<ApplicationRead>("/applications/me/resume"),

  changeLanguage: (language: Language) =>
    request<ApplicationRead>("/applications/me/language", {
      method: "PATCH",
      body: { language },
    }),

  saveField: (fieldId: string, value: FieldValue, source: AnswerSource = "text") =>
    request<FieldUpdateResult>("/applications/me/fields", {
      method: "PUT",
      body: { field_id: fieldId, value, source },
    }),

  confirmField: (fieldId: string, value: FieldValue = null) =>
    request<FieldUpdateResult>("/applications/me/confirm", {
      method: "POST",
      body: { field_id: fieldId, value },
    }),

  listEvents: (afterId?: number, limit = 50) => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (afterId !== undefined) params.set("after_id", String(afterId));
    return request<EventList>(`/applications/me/events?${params}`);
  },
};