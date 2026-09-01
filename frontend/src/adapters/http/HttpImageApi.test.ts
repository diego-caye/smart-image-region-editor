import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { HttpImageApi } from "./HttpImageApi";

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

  it("throws an ApiError carrying the backend's detail message on failure", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ detail: "Image not found" }, 404));

    const api = new HttpImageApi();
    await expect(api.listOperationsForRegion("face")).rejects.toMatchObject({
      status: 404,
      message: "Image not found",
    });
  });
});
