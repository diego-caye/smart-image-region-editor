import type {
  ConfirmEditResult,
  EditGenerationResult,
  ImageApiPort,
  OperationCatalogEntry,
} from "../../application/ports/ImageApiPort";
import type { Region } from "../../domain/entities/Region";
import type { UploadedImage } from "../../domain/entities/UploadedImage";
import type { EditOperation } from "../../domain/types/EditOperation";
import type { EditProgress } from "../../domain/types/EditProgress";
import type { RegionType } from "../../domain/types/RegionType";

/** In-memory ImageApiPort double for component/hook tests — no fetch, no
 * backend needed. Mirrors the backend's tests/unit/application/fakes.py
 * pattern: a Port's contract should be easy to fake. */
export class FakeImageApiPort implements ImageApiPort {
  uploadedFiles: File[] = [];
  nextUploadResult: UploadedImage | Error = {
    imageId: "fake-image-id",
    width: 100,
    height: 100,
    url: "http://example.test/static/original/fake.png",
  };

  analyzedImageIds: string[] = [];
  nextAnalyzeResult: Region[] | Error = [];

  operationsByRegion: Partial<Record<RegionType, OperationCatalogEntry[]>> = {};

  requestedEdits: { imageId: string; regionId: string; operation: EditOperation }[] = [];
  nextEditResult: EditGenerationResult | Error = {
    editId: "fake-edit-id",
    status: "preview_ready",
    previewUrl: "http://example.test/static/preview/fake.png",
    errorMessage: null,
  };

  confirmedEditIds: string[] = [];
  nextConfirmResult: ConfirmEditResult | Error = {
    editId: "fake-edit-id",
    finalUrl: "http://example.test/static/preview/fake.png",
  };

  discardedEditIds: string[] = [];
  nextDiscardError: Error | null = null;

  async uploadImage(file: File): Promise<UploadedImage> {
    this.uploadedFiles.push(file);
    if (this.nextUploadResult instanceof Error) throw this.nextUploadResult;
    return this.nextUploadResult;
  }

  async analyzeImage(imageId: string): Promise<Region[]> {
    this.analyzedImageIds.push(imageId);
    if (this.nextAnalyzeResult instanceof Error) throw this.nextAnalyzeResult;
    return this.nextAnalyzeResult;
  }

  async listOperationsForRegion(regionType: RegionType): Promise<OperationCatalogEntry[]> {
    return this.operationsByRegion[regionType] ?? [];
  }

  /** Set holdEdits to keep requestEdit pending (so a test can push progress
   * through reportProgress) until releaseEdit() is called. */
  holdEdits = false;
  private onProgress: ((progress: EditProgress) => void) | null = null;
  private release: (() => void) | null = null;

  reportProgress(progress: EditProgress): void {
    this.onProgress?.(progress);
  }

  releaseEdit(): void {
    this.release?.();
  }

  async requestEdit(
    imageId: string,
    regionId: string,
    operation: EditOperation,
    onProgress?: (progress: EditProgress) => void,
  ): Promise<EditGenerationResult> {
    this.requestedEdits.push({ imageId, regionId, operation });
    this.onProgress = onProgress ?? null;
    if (this.holdEdits) {
      await new Promise<void>((resolve) => {
        this.release = resolve;
      });
    }
    if (this.nextEditResult instanceof Error) throw this.nextEditResult;
    return this.nextEditResult;
  }

  async confirmEdit(editId: string): Promise<ConfirmEditResult> {
    this.confirmedEditIds.push(editId);
    if (this.nextConfirmResult instanceof Error) throw this.nextConfirmResult;
    return this.nextConfirmResult;
  }

  async discardEdit(editId: string): Promise<void> {
    this.discardedEditIds.push(editId);
    if (this.nextDiscardError) throw this.nextDiscardError;
  }
}
