import type { EditGenerationResult, ImageApiPort } from "../ports/ImageApiPort";
import type { EditOperation } from "../../domain/types/EditOperation";

export async function requestEdit(
  api: ImageApiPort,
  imageId: string,
  regionId: string,
  operation: EditOperation,
): Promise<EditGenerationResult> {
  return api.requestEdit(imageId, regionId, operation);
}
