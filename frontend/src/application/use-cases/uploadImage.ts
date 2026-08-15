import type { UploadedImage } from "../../domain/entities/UploadedImage";
import type { ImageApiPort } from "../ports/ImageApiPort";

export async function uploadImage(api: ImageApiPort, file: File): Promise<UploadedImage> {
  return api.uploadImage(file);
}
