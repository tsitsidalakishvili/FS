"use client";

import { useState } from "react";

const STORAGE_KEY = "delib_participant_id";

function buildRandomId() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `anon-${Math.random().toString(36).slice(2)}`;
}

export function useParticipantId() {
  const [participantId] = useState<string>(() => {
    if (typeof window === "undefined") {
      return "";
    }
    const current = window.localStorage.getItem(STORAGE_KEY);
    if (current) {
      return current;
    }
    const generated = buildRandomId();
    window.localStorage.setItem(STORAGE_KEY, generated);
    return generated;
  });

  return participantId;
}
