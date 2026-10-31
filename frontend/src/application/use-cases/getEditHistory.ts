import type { ImageApiPort } from "../ports/ImageApiPort";
import type { EditHistory } from "../../domain/types/EditHistory";

export async function getEditHistory(api: ImageApiPort, imageId: string): Promise<EditHistory> {
  return api.getEditHistory(imageId);
}
