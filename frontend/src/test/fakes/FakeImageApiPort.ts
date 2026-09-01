import type { ImageApiPort, OperationCatalogEntry } from "../../application/ports/ImageApiPort";
import type { Region } from "../../domain/entities/Region";
import type { UploadedImage } from "../../domain/entities/UploadedImage";
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
}
