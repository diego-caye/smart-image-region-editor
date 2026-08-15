import type { ImageApiPort, OperationCatalogEntry } from "../../application/ports/ImageApiPort";
import type { UploadedImage } from "../../domain/entities/UploadedImage";
import type { EditOperation } from "../../domain/types/EditOperation";
import type { RegionType } from "../../domain/types/RegionType";
import { httpClient, resolveAssetUrl } from "../../infrastructure/api/httpClient";

interface UploadImageResponseBody {
  image_id: string;
  width: number;
  height: number;
  url: string;
}

interface OperationResponseBody {
  operation: EditOperation;
  label: string;
  emoji: string;
}

interface ListOperationsResponseBody {
  region_type: RegionType;
  operations: OperationResponseBody[];
}

/** Implements ImageApiPort against the real backend REST API. This is the
 * only module allowed to know the backend's JSON shape (snake_case keys,
 * response envelopes) — everything above it deals in domain-shaped, camelCase
 * TypeScript objects. */
export class HttpImageApi implements ImageApiPort {
  async uploadImage(file: File): Promise<UploadedImage> {
    const form = new FormData();
    form.append("file", file);
    const body = await httpClient.postForm<UploadImageResponseBody>("/images", form);
    return {
      imageId: body.image_id,
      width: body.width,
      height: body.height,
      url: resolveAssetUrl(body.url),
    };
  }

  async listOperationsForRegion(regionType: RegionType): Promise<OperationCatalogEntry[]> {
    const body = await httpClient.get<ListOperationsResponseBody>(
      `/regions/${regionType}/operations`,
    );
    return body.operations.map((op) => ({
      operation: op.operation,
      label: op.label,
      emoji: op.emoji,
    }));
  }
}
