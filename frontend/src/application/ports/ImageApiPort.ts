import type { Region } from "../../domain/entities/Region";
import type { UploadedImage } from "../../domain/entities/UploadedImage";
import type { EditOperation } from "../../domain/types/EditOperation";
import type { RegionType } from "../../domain/types/RegionType";

export interface OperationCatalogEntry {
  operation: EditOperation;
  label: string;
  emoji: string;
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
}
