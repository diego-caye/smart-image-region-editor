import type { ImageApiPort, UndoResult } from "../ports/ImageApiPort";

export async function undoLastEdit(api: ImageApiPort, imageId: string): Promise<UndoResult> {
  return api.undoLastEdit(imageId);
}
