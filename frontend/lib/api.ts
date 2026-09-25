import { logout } from "../components/auth-provider";

export const API_BASE = (
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "http://127.0.0.1:8000/api/v1"
).replace(/\/+$/, "");

export class ApiError extends Error {
  constructor(
    message: string,
    public status = 0
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function errorText(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "Something went wrong. Please try again.";
}

function detailText(detail: unknown): string {
  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        const location = Array.isArray(item.loc)
          ? item.loc
              .filter((x: string) => x !== "body")
              .join(" → ")
          : "Request";

        return `${location}: ${
          item.msg || "invalid value"
        }`;
      })
      .join(". ");
  }

  if (
    detail &&
    typeof detail === "object" &&
    "message" in detail
  ) {
    return String(detail.message);
  }

  return "The server could not complete this request.";
}

export async function api<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  let response: Response;

  try {
    const token =
      typeof window !== "undefined"
        ? localStorage.getItem(
            "conceptbridge_access_token"
          )
        : null;

    const headers = new Headers(options.headers);

    if (token) {
      headers.set(
        "Authorization",
        `Bearer ${token}`
      );
    }

    response = await fetch(
      `${API_BASE}${path}`,
      {
        ...options,
        headers,
        cache: "no-store",
      }
    );
  } catch (error) {
    if (
      error instanceof DOMException &&
      error.name === "AbortError"
    ) {
      throw error;
    }

    throw new ApiError(
      "Cannot reach ConceptBridge. Keep the backend terminal running on port 8000, then reconnect. If it is running, check the backend's allowed frontend origins."
    );
  }

  const body = await response
    .json()
    .catch(() => null);

  /*
   * JWT EXPIRED / INVALID
   *
   * Backend returns 401 when:
   * - token is expired
   * - token is invalid
   * - user no longer exists
   * - Authorization header is missing for a protected route
   */
  if (response.status === 401) {
    if (typeof window !== "undefined") {
      const currentPath = window.location.pathname;

      /*
       * Do not redirect repeatedly if the user is already
       * on the login or register page.
       */
      if (
        currentPath !== "/login" &&
        currentPath !== "/register"
      ) {
        logout();
      }
    }

    throw new ApiError(
      detailText(body?.detail ?? body) ||
        "Your session has expired. Please log in again.",
      401
    );
  }

  if (!response.ok) {
    throw new ApiError(
      detailText(body?.detail ?? body),
      response.status
    );
  }

  return body as T;
}

export const postJson = <T>(
  path: string,
  body: unknown
) =>
  api<T>(path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

export const patchJson = <T>(
  path: string,
  body: unknown
) =>
  api<T>(path, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

export const postFile = <T>(
  path: string,
  form: FormData
) =>
  api<T>(path, {
    method: "POST",
    body: form,
  });