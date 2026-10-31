import type { EditGenerationResult, ImageApiPort } from "../ports/ImageApiPort";
import type { EditOperation } from "../../domain/types/EditOperation";
import type { EditProgress } from "../../domain/types/EditProgress";

export async function requestEdit(
  api: ImageApiPort,
  imageId: string,
  regionId: string,
  operation: EditOperation,
  onProgress?: (progress: EditProgress) => void,
): Promise<EditGenerationResult> {
  return api.requestEdit(imageId, regionId, operation, onProgress);
}
