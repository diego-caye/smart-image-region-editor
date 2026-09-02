import type { ConfirmEditResult, ImageApiPort } from "../ports/ImageApiPort";

export async function confirmEdit(api: ImageApiPort, editId: string): Promise<ConfirmEditResult> {
  return api.confirmEdit(editId);
}
