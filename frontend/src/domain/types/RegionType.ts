/**
 * Mirrors backend app.domain.value_objects.region_type.RegionType. FACE,
 * LEFT_HAND and RIGHT_HAND are detected in the MVP; MOUTH and EYES are
 * already modeled so the UI has a stable place for them once a detector
 * exists for them server-side.
 */
export type RegionType = "face" | "left_hand" | "right_hand" | "mouth" | "eyes";

export const REGION_LABELS: Record<RegionType, string> = {
  face: "Cara",
  left_hand: "Mano izquierda",
  right_hand: "Mano derecha",
  mouth: "Boca",
  eyes: "Ojos",
};
