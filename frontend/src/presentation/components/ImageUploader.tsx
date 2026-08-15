import { useRef, type ChangeEvent, type DragEvent } from "react";

interface ImageUploaderProps {
  onFileSelected: (file: File) => void;
  isUploading: boolean;
}

/** Step 1 of the flow: pick a photo. Drag-and-drop or a plain file picker —
 * intentionally not fancier than that for the MVP. */
export function ImageUploader({ onFileSelected, isUploading }: ImageUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  function handleChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) onFileSelected(file);
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    const file = event.dataTransfer.files?.[0];
    if (file) onFileSelected(file);
  }

  return (
    <div
      className="image-uploader"
      onDragOver={(event) => event.preventDefault()}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      role="button"
      tabIndex={0}
      aria-busy={isUploading}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        onChange={handleChange}
        disabled={isUploading}
        data-testid="image-uploader-input"
        style={{ display: "none" }}
      />
      <p>{isUploading ? "Subiendo imagen…" : "Arrastra una foto aquí o haz clic para elegirla"}</p>
    </div>
  );
}
