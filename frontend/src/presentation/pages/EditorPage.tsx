import { ImageUploader } from "../components/ImageUploader";
import { useEditSession } from "../hooks/useEditSession";

export function EditorPage() {
  const { status, image, errorMessage, upload } = useEditSession();

  return (
    <main className="editor-page">
      <h1>Smart Image Region Editor</h1>

      {status !== "ready" && (
        <ImageUploader onFileSelected={upload} isUploading={status === "uploading"} />
      )}

      {status === "error" && errorMessage && (
        <p role="alert" className="error-message">
          {errorMessage}
        </p>
      )}

      {image && (
        <section className="uploaded-preview">
          <img src={image.url} alt="Imagen subida" />
          <p>
            {image.width}×{image.height}px — detección de regiones próximamente
          </p>
        </section>
      )}
    </main>
  );
}
