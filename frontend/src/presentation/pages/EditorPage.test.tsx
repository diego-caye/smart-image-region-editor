import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { EditSessionProvider } from "../../infrastructure/state/EditSessionContext";
import { FakeImageApiPort } from "../../test/fakes/FakeImageApiPort";
import { EditorPage } from "./EditorPage";

function renderWithFakeApi(api: FakeImageApiPort) {
  return render(
    <EditSessionProvider api={api}>
      <EditorPage />
    </EditSessionProvider>,
  );
}

async function uploadAFile() {
  const user = userEvent.setup();
  const input = screen.getByTestId("image-uploader-input");
  const file = new File(["fake-bytes"], "photo.png", { type: "image/png" });
  await user.upload(input, file);
  await waitFor(() => expect(screen.getByAltText("Imagen subida")).toBeInTheDocument());
  return user;
}

describe("EditorPage", () => {
  it("shows the uploader first, then the uploaded image after a successful upload", async () => {
    const api = new FakeImageApiPort();
    api.nextUploadResult = {
      imageId: "abc-123",
      width: 640,
      height: 480,
      url: "http://example.test/static/original/abc.png",
    };
    renderWithFakeApi(api);
    await uploadAFile();

    expect(screen.getByAltText("Imagen subida")).toHaveAttribute(
      "src",
      "http://example.test/static/original/abc.png",
    );
    expect(screen.getByText(/640×480px/)).toBeInTheDocument();
    expect(api.uploadedFiles).toHaveLength(1);
  });

  it("shows an error message when the upload fails", async () => {
    const api = new FakeImageApiPort();
    api.nextUploadResult = new Error("Uploaded file is not a valid image");
    renderWithFakeApi(api);

    const user = userEvent.setup();
    const input = screen.getByTestId("image-uploader-input");
    // MIME type must still satisfy the input's accept="image/*" (jsdom/
    // user-event enforce it client-side) — the *content* being invalid is
    // what the backend would reject; here the fake API rejects regardless.
    const file = new File(["not-really-an-image"], "notes.png", { type: "image/png" });

    await user.upload(input, file);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Uploaded file is not a valid image");
    });
  });

  it("walks the full analyze -> select region -> select operation flow", async () => {
    const api = new FakeImageApiPort();
    api.nextAnalyzeResult = [
      {
        regionId: "region-hand",
        regionType: "right_hand",
        boundingBox: { x: 100, y: 100, width: 50, height: 50 },
        confidence: 0.9,
      },
      {
        regionId: "region-face",
        regionType: "face",
        boundingBox: { x: 10, y: 10, width: 80, height: 80 },
        confidence: 0.95,
      },
    ];
    api.operationsByRegion = {
      right_hand: [
        { operation: "peace_sign", label: "Señal de paz", emoji: "✌️" },
        { operation: "wave", label: "Saludar", emoji: "👋" },
      ],
    };
    renderWithFakeApi(api);
    const user = await uploadAFile();

    await user.click(screen.getByRole("button", { name: "Analizar imagen" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Mano derecha" })).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "Cara" })).toBeInTheDocument();
    expect(api.analyzedImageIds).toEqual(["fake-image-id"]);

    await user.click(screen.getByRole("button", { name: "Mano derecha" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Señal de paz/ })).toBeInTheDocument();
    });
    expect(screen.getAllByText("Mano derecha").length).toBeGreaterThan(0); // region label + badge

    await user.click(screen.getByRole("button", { name: /Señal de paz/ }));

    expect(await screen.findByText(/Mano derecha.*Señal de paz/)).toBeInTheDocument();
  });

  it("switching the selected region clears the previous operation selection", async () => {
    const api = new FakeImageApiPort();
    api.nextAnalyzeResult = [
      {
        regionId: "region-right",
        regionType: "right_hand",
        boundingBox: { x: 100, y: 100, width: 50, height: 50 },
        confidence: 0.9,
      },
      {
        regionId: "region-left",
        regionType: "left_hand",
        boundingBox: { x: 200, y: 100, width: 50, height: 50 },
        confidence: 0.9,
      },
    ];
    api.operationsByRegion = {
      right_hand: [{ operation: "peace_sign", label: "Señal de paz", emoji: "✌️" }],
      left_hand: [{ operation: "fist", label: "Puño", emoji: "✊" }],
    };
    renderWithFakeApi(api);
    const user = await uploadAFile();
    await user.click(screen.getByRole("button", { name: "Analizar imagen" }));
    await waitFor(() => screen.getByRole("button", { name: "Mano derecha" }));

    await user.click(screen.getByRole("button", { name: "Mano derecha" }));
    await waitFor(() => screen.getByRole("button", { name: /Señal de paz/ }));
    await user.click(screen.getByRole("button", { name: /Señal de paz/ }));
    expect(await screen.findByText("3. Vista previa")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Mano izquierda" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Puño/ })).toBeInTheDocument();
    });
    expect(screen.queryByText("3. Vista previa")).not.toBeInTheDocument();
  });
});
