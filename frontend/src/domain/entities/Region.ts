import type { BoundingBox } from "../value-objects/BoundingBox";
import type { RegionType } from "../types/RegionType";

export interface Region {
  regionId: string;
  regionType: RegionType;
  boundingBox: BoundingBox;
  confidence: number;
}
