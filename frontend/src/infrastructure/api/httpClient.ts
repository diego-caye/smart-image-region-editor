/**
 * The one place that knows the backend's base URL and how to turn a failed
 * fetch into an error. adapters/http/* are the only callers.
 */

// 8420, not 8000: the default 8000 is already used by another project on
// this machine (see ../../../.env.example at the repo root).
const BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8420";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, init);
  if (!response.ok) {
    const detail = await safeReadDetail(response);
    throw new ApiError(response.status, detail ?? `Request to ${path} failed with ${response.status}`);
  }
  return (await response.json()) as T;
}

async function safeReadDetail(response: Response): Promise<string | null> {
  try {
    const body: unknown = await response.json();
    if (body && typeof body === "object" && "detail" in body && typeof body.detail === "string") {
      return body.detail;
    }
    return null;
  } catch {
    return null;
  }
}

export const httpClient = {
  get: <T>(path: string): Promise<T> => request<T>(path),
  post: <T>(path: string): Promise<T> => request<T>(path, { method: "POST" }),
  postForm: <T>(path: string, form: FormData): Promise<T> =>
    request<T>(path, { method: "POST", body: form }),
};

/** Backend URLs (e.g. from ImageStorage.url_for) are root-relative; this is
 * the one place that joins them back to an absolute, loadable URL. */
export function resolveAssetUrl(url: string): string {
  return url.startsWith("http") ? url : `${BASE_URL}${url}`;
}
