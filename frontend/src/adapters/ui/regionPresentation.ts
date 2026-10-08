import type { RegionType } from "../../domain/types/RegionType";

/**
 * Region -> display metadata. Presentation concern (adapters/ui, per
 * docs/architecture.md), deliberately separate from the pure RegionType.
 */

export const REGION_LABELS: Record<RegionType, string> = {
  face: "Face",
  left_hand: "Left hand",
  right_hand: "Right hand",
  mouth: "Mouth",
  eyes: "Eyes",
  body: "Body",
};

export const REGION_COLORS: Record<RegionType, string> = {
  face: "#f97316",
  left_hand: "#3b82f6",
  right_hand: "#22c55e",
  mouth: "#ec4899",
  eyes: "#a855f7",
  body: "#0ea5e9",
};
