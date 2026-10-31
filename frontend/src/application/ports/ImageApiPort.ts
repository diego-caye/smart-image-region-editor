import type { Region } from "../../domain/entities/Region";
import type { UploadedImage } from "../../domain/entities/UploadedImage";
import type { EditHistory } from "../../domain/types/EditHistory";
import type { EditOperation } from "../../domain/types/EditOperation";
import type { EditProgress } from "../../domain/types/EditProgress";
import type { GarmentColor } from "../../domain/types/GarmentColor";
import type { RegionType } from "../../domain/types/RegionType";

export interface OperationCatalogEntry {
  operation: EditOperation;
  label: string;
  emoji: string;
  /** The palette to pick from; empty when the operation takes no color. */
  colors: GarmentColor[];
}

export interface EditGenerationResult {
  editId: string;
  status: "preview_ready" | "failed";
  previewUrl: string | null;
  errorMessage: string | null;
}

export interface ConfirmEditResult {
  editId: string;
  finalUrl: string;
}

export interface UndoResult {
  revertedEditId: string;
  currentUrl: string;
}

/**
 * Everything Application knows about talking to a backend — no fetch, no
 * endpoint paths, no HTTP status codes here. adapters/http/HttpImageApi is
 * the (currently only) implementation; a component never imports it
 * directly, only through presentation/hooks -> application/use-cases.
 */
export interface ImageApiPort {
  uploadImage(file: File): Promise<UploadedImage>;
  analyzeImage(imageId: string): Promise<Region[]>;
  listOperationsForRegion(regionType: RegionType): Promise<OperationCatalogEntry[]>;
  /** onProgress, if given, is called with the edit's progress while the
   * returned promise is still pending — an edit takes on the order of a
   * minute. color must be set exactly when the operation's catalog entry
   * lists colors. */
  requestEdit(
    imageId: string,
    regionId: string,
    operation: EditOperation,
    color: GarmentColor | null,
    onProgress?: (progress: EditProgress) => void,
  ): Promise<EditGenerationResult>;
  confirmEdit(editId: string): Promise<ConfirmEditResult>;
  discardEdit(editId: string): Promise<void>;
  getEditHistory(imageId: string): Promise<EditHistory>;
  /** Reverts the last applied edit; the image goes back to what it was
   * before it. */
  undoLastEdit(imageId: string): Promise<UndoResult>;
  /** Where the current image can be downloaded from, as a file. */
  downloadUrl(imageId: string): string;
}
