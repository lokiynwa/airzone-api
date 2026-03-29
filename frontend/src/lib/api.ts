const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

type ApiErrorShape = {
  detail?: string;
};

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    let errorMessage = "Request failed.";

    try {
      const body = (await response.json()) as ApiErrorShape;
      if (body.detail) {
        errorMessage = body.detail;
      }
    } catch {
      errorMessage = `Request failed with status ${response.status}.`;
    }

    throw new Error(errorMessage);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

