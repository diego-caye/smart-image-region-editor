import { useRef, type ChangeEvent, type DragEvent } from "react";
import { cn } from "../lib/utils";

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
      className={cn(
        "flex cursor-pointer flex-col items-center gap-2 rounded-xl border-2 border-dashed border-border bg-card px-6 py-14 text-center transition-colors",
        "hover:border-primary focus-visible:border-primary focus-visible:outline-none",
      )}
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
        className="hidden"
      />
      <span className="text-3xl" aria-hidden="true">
        📷
      </span>
      <p className="text-sm text-muted-foreground">
        {isUploading ? "Uploading image…" : "Drag a photo here or click to choose one"}
      </p>
    </div>
  );
}
