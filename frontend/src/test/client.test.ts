import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiFetch, resetClientForTests, setAccessToken } from "../api/client";

describe("apiFetch refresh", () => {
  beforeEach(() => {
    resetClientForTests();
    vi.restoreAllMocks();
  });

  it("tenta refresh apenas uma vez em 401", async () => {
    setAccessToken("expired");
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({}),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ access_token: "new-token" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ ok: true }),
      });

    vi.stubGlobal("fetch", fetchMock);

    const result = await apiFetch<{ ok: boolean }>("/api/v1/stations");
    expect(result.ok).toBe(true);
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock.mock.calls[1][0]).toContain("/api/v1/auth/refresh");
  });

  it("encerra sessão quando refresh falha", async () => {
    setAccessToken("expired");
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: false, status: 401, json: async () => ({}) })
      .mockResolvedValueOnce({ ok: false, status: 401, json: async () => ({}) });

    vi.stubGlobal("fetch", fetchMock);

    await expect(apiFetch("/api/v1/stations")).rejects.toThrow();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
