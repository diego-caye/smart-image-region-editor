import type { GarmentColor } from "../../domain/types/GarmentColor";

/** GarmentColor -> swatch display. Presentation only, like regionPresentation. */
export const GARMENT_COLOR_LABELS: Record<GarmentColor, string> = {
  red: "Red",
  blue: "Blue",
  green: "Green",
  yellow: "Yellow",
  black: "Black",
  white: "White",
  gray: "Gray",
};

export const GARMENT_COLOR_SWATCHES: Record<GarmentColor, string> = {
  red: "#dc2626",
  blue: "#2563eb",
  green: "#16a34a",
  yellow: "#eab308",
  black: "#111827",
  white: "#f9fafb",
  gray: "#6b7280",
};
