const trimTrailingSlash = (value: string | undefined) =>
  (value ?? '').trim().replace(/\/+$/, '')

export const coreApiBaseUrl = trimTrailingSlash(import.meta.env.VITE_CORE_API_URL)
export const deliberationApiBaseUrl = trimTrailingSlash(
  import.meta.env.VITE_DELIBERATION_API_URL,
)

export async function fetchJson<T>(
  input: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(input, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  })

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `Request failed: ${response.status}`)
  }

  return (await response.json()) as T
}
