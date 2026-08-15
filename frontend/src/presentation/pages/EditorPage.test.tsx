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

    const user = userEvent.setup();
    const input = screen.getByTestId("image-uploader-input");
    const file = new File(["fake-bytes"], "photo.png", { type: "image/png" });

    await user.upload(input, file);

    await waitFor(() => {
      expect(screen.getByAltText("Imagen subida")).toHaveAttribute(
        "src",
        "http://example.test/static/original/abc.png",
      );
    });
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
});
