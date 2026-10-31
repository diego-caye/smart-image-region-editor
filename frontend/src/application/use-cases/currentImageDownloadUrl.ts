import type { ImageApiPort } from "../ports/ImageApiPort";

export function currentImageDownloadUrl(api: ImageApiPort, imageId: string): string {
  return api.downloadUrl(imageId);
}
