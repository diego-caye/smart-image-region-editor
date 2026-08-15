import type { RegionType } from "../../domain/types/RegionType";
import type { ImageApiPort, OperationCatalogEntry } from "../ports/ImageApiPort";

export async function listOperationsForRegion(
  api: ImageApiPort,
  regionType: RegionType,
): Promise<OperationCatalogEntry[]> {
  return api.listOperationsForRegion(regionType);
}
