import type { ImageApiPort } from "../ports/ImageApiPort";

export async function discardEdit(api: ImageApiPort, editId: string): Promise<void> {
  return api.discardEdit(editId);
}
