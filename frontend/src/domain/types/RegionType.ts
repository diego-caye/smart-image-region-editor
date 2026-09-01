/**
 * Mirrors backend app.domain.value_objects.region_type.RegionType. FACE,
 * LEFT_HAND and RIGHT_HAND are detected in the MVP; MOUTH and EYES are
 * already modeled so the UI has a stable place for them once a detector
 * exists for them server-side. Display metadata (labels, colors) lives in
 * adapters/ui/regionPresentation.ts, not here — this stays a pure type.
 */
export type RegionType = "face" | "left_hand" | "right_hand" | "mouth" | "eyes";
