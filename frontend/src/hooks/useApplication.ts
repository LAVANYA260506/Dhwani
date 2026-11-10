"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError, api } from "../lib/api";
import { clearToken, getToken, setToken } from "../lib/session";
import type {
  AnswerSource,
  ApplicationRead,
  FieldUpdateResult,
  FieldValue,
  Language,
} from "../lib/types";

/** Apply a save result to local state straight away, so the UI reacts
 *  instantly. A background refresh then replaces it with the server's truth. */
function applyResult(
  app: ApplicationRead,
  result: FieldUpdateResult
): ApplicationRead {
  const values = { ...app.values };
  if (result.accepted) {
    if (result.value === null || result.value === undefined) {
      delete values[result.field_id];
    } else {
      values[result.field_id] = result.value;
    }
    for (const [fieldId, value] of Object.entries(result.auto_filled)) {
      if (value === null) delete values[fieldId];
      else values[fieldId] = value;
    }
  }
  return {
    ...app,
    values,
    current_field: result.next_field,
    progress: result.progress ?? app.progress,
    field_status: result.field_status ?? app.field_status,
  };
}

export function useApplication() {
  const [application, setApplication] = useState<ApplicationRead | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Issues from the last rejected answer, for showing a correction hint
  const [lastResult, setLastResult] = useState<FieldUpdateResult | null>(null);
  const refreshSeq = useRef(0);

  const handleError = useCallback((err: unknown) => {
    if (err instanceof ApiError && err.status === 401) {
      // Session no longer valid: forget it so the user can start again
      clearToken();
      setApplication(null);
    }
    setError(err instanceof Error ? err.message : "Something went wrong.");
  }, []);

  /** Re-read the full state from the server (the source of truth). */
  const refresh = useCallback(async () => {
    const seq = ++refreshSeq.current;
    try {
      const fresh = await api.getApplication();
      if (seq === refreshSeq.current) setApplication(fresh);
    } catch (err) {
      handleError(err);
    }
  }, [handleError]);

  // Resume an existing session on first load
  useEffect(() => {
    let cancelled = false;
    async function resume() {
      if (!getToken()) {
        setLoading(false);
        return;
      }
      try {
        const state = await api.resumeApplication();
        if (!cancelled) setApplication(state);
      } catch (err) {
        if (!cancelled) handleError(err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    resume();
    return () => {
      cancelled = true;
    };
  }, [handleError]);

  const start = useCallback(
    async (language: Language, consentGiven: boolean) => {
      setError(null);
      try {
        const created = await api.createApplication(language, consentGiven);
        setToken(created.session_token);
        setApplication(await api.getApplication());
      } catch (err) {
        handleError(err);
      }
    },
    [handleError]
  );

  const saveField = useCallback(
    async (
      fieldId: string,
      value: FieldValue,
      source: AnswerSource = "text"
    ): Promise<FieldUpdateResult | null> => {
      setError(null);
      try {
        const result = await api.saveField(fieldId, value, source);
        setLastResult(result);
        setApplication((prev) => (prev ? applyResult(prev, result) : prev));
        if (result.accepted) void refresh();
        return result;
      } catch (err) {
        handleError(err);
        return null;
      }
    },
    [handleError, refresh]
  );

  const confirmField = useCallback(
    async (fieldId: string, value: FieldValue = null) => {
      setError(null);
      try {
        const result = await api.confirmField(fieldId, value);
        setLastResult(result);
        setApplication((prev) => (prev ? applyResult(prev, result) : prev));
        void refresh();
        return result;
      } catch (err) {
        handleError(err);
        return null;
      }
    },
    [handleError, refresh]
  );

  const changeLanguage = useCallback(
    async (language: Language) => {
      setError(null);
      try {
        setApplication(await api.changeLanguage(language));
      } catch (err) {
        handleError(err);
      }
    },
    [handleError]
  );

   const reset = useCallback(async () => {
    try {
      await api.deleteApplication(); // remove the data from the server
    } catch {
      /* already gone or session invalid: carry on */
    }
    clearToken();
    setApplication(null);
    setLastResult(null);
  }, []);

  return {
    application,
    loading,
    error,
    lastResult,
    start,
    saveField,
    confirmField,
    changeLanguage,
    refresh,
    reset,
  };

} 