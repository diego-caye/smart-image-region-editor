import type {
  ConfirmEditResult,
  EditGenerationResult,
  ImageApiPort,
  OperationCatalogEntry,
} from "../../application/ports/ImageApiPort";
import type { Region } from "../../domain/entities/Region";
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

interface RegionResponseBody {
  region_id: string;
  region_type: RegionType;
  x: number;
  y: number;
  width: number;
  height: number;
  confidence: number;
}

interface AnalyzeImageResponseBody {
  image_id: string;
  regions: RegionResponseBody[];
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

interface EditRegionResponseBody {
  edit_id: string;
  status: "preview_ready" | "failed";
  preview_url: string | null;
  error_message: string | null;
}

interface ConfirmEditResponseBody {
  edit_id: string;
  status: string;
  final_url: string;
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

  async analyzeImage(imageId: string): Promise<Region[]> {
    const body = await httpClient.post<AnalyzeImageResponseBody>(`/images/${imageId}/analyze`);
    return body.regions.map(regionFromResponseBody);
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

  async requestEdit(
    imageId: string,
    regionId: string,
    operation: EditOperation,
  ): Promise<EditGenerationResult> {
    const body = await httpClient.postJson<EditRegionResponseBody>(`/images/${imageId}/edits`, {
      region_id: regionId,
      operation,
    });
    return {
      editId: body.edit_id,
      status: body.status,
      previewUrl: body.preview_url ? resolveAssetUrl(body.preview_url) : null,
      errorMessage: body.error_message,
    };
  }

  async confirmEdit(editId: string): Promise<ConfirmEditResult> {
    const body = await httpClient.post<ConfirmEditResponseBody>(`/edits/${editId}/confirm`);
    return { editId: body.edit_id, finalUrl: resolveAssetUrl(body.final_url) };
  }

  async discardEdit(editId: string): Promise<void> {
    await httpClient.post(`/edits/${editId}/discard`);
  }
}

function regionFromResponseBody(body: RegionResponseBody): Region {
  return {
    regionId: body.region_id,
    regionType: body.region_type,
    boundingBox: { x: body.x, y: body.y, width: body.width, height: body.height },
    confidence: body.confidence,
  };
}
