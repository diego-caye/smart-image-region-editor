import type { Region } from "../../domain/entities/Region";
import type { ImageApiPort } from "../ports/ImageApiPort";

export async function analyzeImage(api: ImageApiPort, imageId: string): Promise<Region[]> {
  return api.analyzeImage(imageId);
}
