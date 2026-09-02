import type { Region } from "../../domain/entities/Region";
import type { UploadedImage } from "../../domain/entities/UploadedImage";
import type { EditOperation } from "../../domain/types/EditOperation";
import type { RegionType } from "../../domain/types/RegionType";

export interface OperationCatalogEntry {
  operation: EditOperation;
  label: string;
  emoji: string;
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
  requestEdit(imageId: string, regionId: string, operation: EditOperation): Promise<EditGenerationResult>;
  confirmEdit(editId: string): Promise<ConfirmEditResult>;
  discardEdit(editId: string): Promise<void>;
}
