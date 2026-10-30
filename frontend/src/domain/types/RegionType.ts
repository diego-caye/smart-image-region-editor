/**
 * Mirrors backend app.domain.value_objects.region_type.RegionType. All ten
 * are detected server-side. Display metadata (labels, colors) lives
 * in adapters/ui/regionPresentation.ts, not here — this stays a pure type.
 */
export type RegionType =
  | "face"
  | "left_hand"
  | "right_hand"
  | "mouth"
  | "eyes"
  | "body"
  | "torso"
  | "left_arm"
  | "right_arm"
  | "legs";
