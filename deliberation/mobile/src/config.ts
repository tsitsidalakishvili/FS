import Constants from "expo-constants";

const fromExpoExtra = (Constants.expoConfig?.extra?.deliberationApiUrl as string | undefined) ?? "";
const fromEnv =
  (globalThis as { process?: { env?: Record<string, string | undefined> } }).process?.env
    ?.EXPO_PUBLIC_DELIBERATION_API_URL ?? "";

export const API_BASE_URL = (fromEnv || fromExpoExtra || "http://localhost:8010").replace(/\/+$/, "");
