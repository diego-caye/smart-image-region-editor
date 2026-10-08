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
  await waitFor(() => expect(screen.getByAltText("Uploaded image")).toBeInTheDocument());
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

    expect(screen.getByAltText("Uploaded image")).toHaveAttribute(
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
        { operation: "peace_sign", label: "Peace sign", emoji: "✌️" },
        { operation: "wave", label: "Wave", emoji: "👋" },
      ],
    };
    renderWithFakeApi(api);
    const user = await uploadAFile();

    await user.click(screen.getByRole("button", { name: "Analyze image" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Right hand" })).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "Face" })).toBeInTheDocument();
    expect(api.analyzedImageIds).toEqual(["fake-image-id"]);

    await user.click(screen.getByRole("button", { name: "Right hand" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Peace sign/ })).toBeInTheDocument();
    });
    expect(screen.getAllByText("Right hand").length).toBeGreaterThan(0); // region label + badge

    await user.click(screen.getByRole("button", { name: /Peace sign/ }));

    expect(await screen.findByText(/Right hand.*Peace sign/)).toBeInTheDocument();
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
      right_hand: [{ operation: "peace_sign", label: "Peace sign", emoji: "✌️" }],
      left_hand: [{ operation: "fist", label: "Fist", emoji: "✊" }],
    };
    renderWithFakeApi(api);
    const user = await uploadAFile();
    await user.click(screen.getByRole("button", { name: "Analyze image" }));
    await waitFor(() => screen.getByRole("button", { name: "Right hand" }));

    await user.click(screen.getByRole("button", { name: "Right hand" }));
    await waitFor(() => screen.getByRole("button", { name: /Peace sign/ }));
    await user.click(screen.getByRole("button", { name: /Peace sign/ }));
    expect(await screen.findByText("3. Preview")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Left hand" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Fist/ })).toBeInTheDocument();
    });
    expect(screen.queryByText("3. Preview")).not.toBeInTheDocument();
  });

  async function setUpToOperationSelected(api: FakeImageApiPort) {
    api.nextAnalyzeResult = [
      {
        regionId: "region-hand",
        regionType: "right_hand",
        boundingBox: { x: 100, y: 100, width: 50, height: 50 },
        confidence: 0.9,
      },
    ];
    api.operationsByRegion = {
      right_hand: [{ operation: "peace_sign", label: "Peace sign", emoji: "✌️" }],
    };
    renderWithFakeApi(api);
    const user = await uploadAFile();
    await user.click(screen.getByRole("button", { name: "Analyze image" }));
    await waitFor(() => screen.getByRole("button", { name: "Right hand" }));
    await user.click(screen.getByRole("button", { name: "Right hand" }));
    await waitFor(() => screen.getByRole("button", { name: /Peace sign/ }));
    await user.click(screen.getByRole("button", { name: /Peace sign/ }));
    return user;
  }

  it("generates a preview and accepting it updates the image and resets selection", async () => {
    const api = new FakeImageApiPort();
    api.nextEditResult = {
      editId: "edit-1",
      status: "preview_ready",
      previewUrl: "http://example.test/static/preview/edit-1.png",
      errorMessage: null,
    };
    api.nextConfirmResult = { editId: "edit-1", finalUrl: "http://example.test/static/preview/final.png" };
    const user = await setUpToOperationSelected(api);

    await user.click(screen.getByRole("button", { name: "Generate preview" }));

    await waitFor(() => {
      expect(screen.getByAltText("After")).toHaveAttribute(
        "src",
        "http://example.test/static/preview/edit-1.png",
      );
    });
    expect(api.requestedEdits).toEqual([
      { imageId: "fake-image-id", regionId: "region-hand", operation: "peace_sign" },
    ]);

    await user.click(screen.getByRole("button", { name: "Accept" }));

    await waitFor(() => {
      expect(screen.getByAltText("Uploaded image")).toHaveAttribute(
        "src",
        "http://example.test/static/preview/final.png",
      );
    });
    expect(api.confirmedEditIds).toEqual(["edit-1"]);
    // selection resets so the user can pick another region for a second edit
    expect(screen.queryByText("2. Choose a transformation")).not.toBeInTheDocument();
  });

  it("shows the backend's failure message and lets the user retry", async () => {
    const api = new FakeImageApiPort();
    api.nextEditResult = {
      editId: "edit-1",
      status: "failed",
      previewUrl: null,
      errorMessage: "ComfyUI timed out",
    };
    const user = await setUpToOperationSelected(api);

    await user.click(screen.getByRole("button", { name: "Generate preview" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("ComfyUI timed out");
    });
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("discarding a preview clears it but keeps the operation gallery open", async () => {
    const api = new FakeImageApiPort();
    const user = await setUpToOperationSelected(api);

    await user.click(screen.getByRole("button", { name: "Generate preview" }));
    await waitFor(() => screen.getByRole("button", { name: "Discard" }));

    await user.click(screen.getByRole("button", { name: "Discard" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Generate preview" })).toBeInTheDocument();
    });
    expect(api.discardedEditIds).toEqual(["fake-edit-id"]);
    // still on the same region's operation gallery, not reset further
    expect(screen.getByText("2. Choose a transformation")).toBeInTheDocument();
  });
});
