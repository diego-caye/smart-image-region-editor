import type {
  ConfirmEditResult,
  EditGenerationResult,
  ImageApiPort,
  OperationCatalogEntry,
  UndoResult,
} from "../../application/ports/ImageApiPort";
import type { Region } from "../../domain/entities/Region";
import type { UploadedImage } from "../../domain/entities/UploadedImage";
import type { EditHistory } from "../../domain/types/EditHistory";
import type { EditOperation } from "../../domain/types/EditOperation";
import type { EditProgress } from "../../domain/types/EditProgress";
import type { GarmentColor } from "../../domain/types/GarmentColor";
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
  colors: GarmentColor[];
}

interface ListOperationsResponseBody {
  region_type: RegionType;
  operations: OperationResponseBody[];
}

interface EditHistoryResponseBody {
  entries: {
    edit_id: string;
    region_type: RegionType | null;
    operation: EditOperation;
    label: string;
    emoji: string;
    color: GarmentColor | null;
    status: "confirmed" | "reverted";
  }[];
  can_undo: boolean;
}

interface UndoResponseBody {
  reverted_edit_id: string;
  current_url: string;
}

interface EditRegionResponseBody {
  edit_id: string;
  status: "preview_ready" | "failed";
  preview_url: string | null;
  error_message: string | null;
}

/** Same shape as EditProgress, field names included. */
type EditProgressResponseBody = EditProgress;

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
      colors: op.colors,
    }));
  }

  async requestEdit(
    imageId: string,
    regionId: string,
    operation: EditOperation,
    color: GarmentColor | null,
    onProgress?: (progress: EditProgress) => void,
  ): Promise<EditGenerationResult> {
    // The POST only answers once the edit is done, so progress is read
    // from a separate endpoint, keyed by an id we choose up front.
    const progressId = newProgressId();
    const request = httpClient.postJson<EditRegionResponseBody>(`/images/${imageId}/edits`, {
      region_id: regionId,
      operation,
      ...(color ? { color } : {}),
      progress_id: progressId,
    });
    const stopPolling = onProgress ? pollProgress(progressId, onProgress) : () => {};
    try {
      const body = await request;
      return {
        editId: body.edit_id,
        status: body.status,
        previewUrl: body.preview_url ? resolveAssetUrl(body.preview_url) : null,
        errorMessage: body.error_message,
      };
    } finally {
      stopPolling();
    }
  }

  async confirmEdit(editId: string): Promise<ConfirmEditResult> {
    const body = await httpClient.post<ConfirmEditResponseBody>(`/edits/${editId}/confirm`);
    return { editId: body.edit_id, finalUrl: resolveAssetUrl(body.final_url) };
  }

  async discardEdit(editId: string): Promise<void> {
    await httpClient.post(`/edits/${editId}/discard`);
  }

  async getEditHistory(imageId: string): Promise<EditHistory> {
    const body = await httpClient.get<EditHistoryResponseBody>(`/images/${imageId}/history`);
    return {
      entries: body.entries.map((e) => ({
        editId: e.edit_id,
        regionType: e.region_type,
        operation: e.operation,
        label: e.label,
        emoji: e.emoji,
        color: e.color,
        status: e.status,
      })),
      canUndo: body.can_undo,
    };
  }

  async undoLastEdit(imageId: string): Promise<UndoResult> {
    const body = await httpClient.post<UndoResponseBody>(`/images/${imageId}/undo`);
    return { revertedEditId: body.reverted_edit_id, currentUrl: resolveAssetUrl(body.current_url) };
  }

  downloadUrl(imageId: string): string {
    return resolveAssetUrl(`/images/${imageId}/download`);
  }
}

export const PROGRESS_POLL_INTERVAL_MS = 1000;

/** Polls until the returned stop function is called. Best-effort: a 404 is
 * normal before the edit reports anything, and any other failure just
 * means one missed update — never a reason to fail the edit itself. */
function pollProgress(progressId: string, onProgress: (progress: EditProgress) => void) {
  let stopped = false;
  void (async () => {
    while (!stopped) {
      await new Promise((resolve) => setTimeout(resolve, PROGRESS_POLL_INTERVAL_MS));
      if (stopped) break;
      try {
        const body = await httpClient.get<EditProgressResponseBody>(`/edits/progress/${progressId}`);
        // The edit may have finished while this request was in flight.
        if (!stopped) onProgress(body);
      } catch {
        // see docstring
      }
    }
  })();
  return () => {
    stopped = true;
  };
}

/** crypto.randomUUID only exists in secure contexts — opening the app over
 * a LAN IP (plain http) would lack it. */
function newProgressId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
}

function regionFromResponseBody(body: RegionResponseBody): Region {
  return {
    regionId: body.region_id,
    regionType: body.region_type,
    boundingBox: { x: body.x, y: body.y, width: body.width, height: body.height },
    confidence: body.confidence,
  };
}
