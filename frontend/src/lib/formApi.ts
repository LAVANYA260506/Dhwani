import { ApiError } from "./api";
import type { FormDefinition } from "./types";

const BASE_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

/** The form definition is public: it is the same for everyone. */
export async function getForm(): Promise<FormDefinition> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}/api/form`);
  } catch {
    throw new ApiError(0, "network_error", "Cannot reach the server. Please try again.");
  }
  if (!response.ok) {
    throw new ApiError(response.status, "http_error", `Could not load the form (${response.status}).`);
  }
  return (await response.json()) as FormDefinition;
}