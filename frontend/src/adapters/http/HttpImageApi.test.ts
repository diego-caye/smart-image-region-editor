import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { EditProgress } from "../../domain/types/EditProgress";
import { HttpImageApi, PROGRESS_POLL_INTERVAL_MS } from "./HttpImageApi";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("HttpImageApi", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("maps the backend's snake_case upload response to a domain UploadedImage", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({
        image_id: "img-1",
        width: 800,
        height: 600,
        url: "/static/original/img-1.png",
      }),
    );

    const api = new HttpImageApi();
    const file = new File(["bytes"], "photo.png", { type: "image/png" });
    const result = await api.uploadImage(file);

    expect(result).toEqual({
      imageId: "img-1",
      width: 800,
      height: 600,
      url: "http://127.0.0.1:8420/static/original/img-1.png",
    });

    const [, init] = vi.mocked(fetch).mock.calls[0];
    expect(init?.method).toBe("POST");
    expect(init?.body).toBeInstanceOf(FormData);
  });

  it("maps the backend's snake_case analyze response to domain Regions and POSTs with no body", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({
        image_id: "img-1",
        regions: [
          {
            region_id: "r1",
            region_type: "right_hand",
            x: 10,
            y: 20,
            width: 30,
            height: 40,
            confidence: 0.75,
          },
        ],
      }),
    );

    const api = new HttpImageApi();
    const regions = await api.analyzeImage("img-1");

    expect(regions).toEqual([
      {
        regionId: "r1",
        regionType: "right_hand",
        boundingBox: { x: 10, y: 20, width: 30, height: 40 },
        confidence: 0.75,
      },
    ]);

    const [url, init] = vi.mocked(fetch).mock.calls[0];
    expect(url).toBe("http://127.0.0.1:8420/images/img-1/analyze");
    expect(init?.method).toBe("POST");
    expect(init?.body).toBeUndefined();
  });

  it("requestEdit POSTs a JSON body and maps a preview_ready response", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({
        edit_id: "edit-1",
        status: "preview_ready",
        preview_url: "/static/preview/edit-1.png",
        error_message: null,
      }),
    );

    const api = new HttpImageApi();
    const result = await api.requestEdit("img-1", "region-1", "peace_sign", null);

    expect(result).toEqual({
      editId: "edit-1",
      status: "preview_ready",
      previewUrl: "http://127.0.0.1:8420/static/preview/edit-1.png",
      errorMessage: null,
    });

    const [url, init] = vi.mocked(fetch).mock.calls[0];
    expect(url).toBe("http://127.0.0.1:8420/images/img-1/edits");
    expect(init?.method).toBe("POST");
    expect(init?.headers).toMatchObject({ "Content-Type": "application/json" });
    expect(JSON.parse(init?.body as string)).toEqual({
      region_id: "region-1",
      operation: "peace_sign",
      progress_id: expect.stringMatching(/^[A-Za-z0-9_-]{1,64}$/),
    });
  });

  it("requestEdit sends the color only when one is chosen", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({ edit_id: "e", status: "preview_ready", preview_url: "/p.png", error_message: null }),
    );

    await new HttpImageApi().requestEdit("img-1", "region-1", "hoodie", "green");

    const [, init] = vi.mocked(fetch).mock.calls[0];
    expect(JSON.parse(init?.body as string)).toMatchObject({ operation: "hoodie", color: "green" });
  });

  it("requestEdit polls the edit's progress while it runs and stops once it ends", async () => {
    vi.useFakeTimers();
    let finishEdit!: (response: Response) => void;
    vi.mocked(fetch).mockImplementation((input) => {
      if (String(input).includes("/edits/progress/")) {
        return Promise.resolve(
          jsonResponse({ stage: "generating", fraction: 0.575, step: 2, steps: 4 }),
        );
      }
      return new Promise<Response>((resolve) => {
        finishEdit = resolve;
      });
    });

    const reports: EditProgress[] = [];
    const pending = new HttpImageApi().requestEdit("img-1", "region-1", "wave", null, (p) => reports.push(p));
    await vi.advanceTimersByTimeAsync(PROGRESS_POLL_INTERVAL_MS * 2 + 10);

    expect(reports).toEqual([
      { stage: "generating", fraction: 0.575, step: 2, steps: 4 },
      { stage: "generating", fraction: 0.575, step: 2, steps: 4 },
    ]);
    const calls = vi.mocked(fetch).mock.calls;
    const { progress_id } = JSON.parse(calls[0][1]?.body as string);
    expect(calls[1][0]).toBe(`http://127.0.0.1:8420/edits/progress/${progress_id}`);

    finishEdit(
      jsonResponse({ edit_id: "e1", status: "preview_ready", preview_url: "/p.png", error_message: null }),
    );
    await pending;
    const callsWhenDone = calls.length;
    await vi.advanceTimersByTimeAsync(PROGRESS_POLL_INTERVAL_MS * 3);
    expect(calls.length).toBe(callsWhenDone);
  });

  it("requestEdit maps a failed response without a null preview_url crashing resolveAssetUrl", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({
        edit_id: "edit-1",
        status: "failed",
        preview_url: null,
        error_message: "ComfyUI timed out",
      }),
    );

    const api = new HttpImageApi();
    const result = await api.requestEdit("img-1", "region-1", "peace_sign", null);

    expect(result).toEqual({
      editId: "edit-1",
      status: "failed",
      previewUrl: null,
      errorMessage: "ComfyUI timed out",
    });
  });

  it("confirmEdit maps the final_url response", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({ edit_id: "edit-1", status: "confirmed", final_url: "/static/preview/final.png" }),
    );

    const api = new HttpImageApi();
    const result = await api.confirmEdit("edit-1");

    expect(result).toEqual({
      editId: "edit-1",
      finalUrl: "http://127.0.0.1:8420/static/preview/final.png",
    });
    const [url] = vi.mocked(fetch).mock.calls[0];
    expect(url).toBe("http://127.0.0.1:8420/edits/edit-1/confirm");
  });

  it("discardEdit POSTs to the right endpoint", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ edit_id: "edit-1", status: "discarded" }));

    const api = new HttpImageApi();
    await api.discardEdit("edit-1");

    const [url, init] = vi.mocked(fetch).mock.calls[0];
    expect(url).toBe("http://127.0.0.1:8420/edits/edit-1/discard");
    expect(init?.method).toBe("POST");
  });

  it("throws an ApiError carrying the backend's detail message on failure", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ detail: "Image not found" }, 404));

    const api = new HttpImageApi();
    await expect(api.listOperationsForRegion("face")).rejects.toMatchObject({
      status: 404,
      message: "Image not found",
    });
  });
});
