import {
  GARMENT_COLOR_LABELS,
  GARMENT_COLOR_SWATCHES,
} from "../../adapters/ui/garmentColorPresentation";
import type { GarmentColor } from "../../domain/types/GarmentColor";
import { cn } from "../lib/utils";

interface ColorSwatchesProps {
  colors: GarmentColor[];
  selectedColor: GarmentColor | null;
  onSelectColor: (color: GarmentColor) => void;
}

/** A row of color swatches for garment operations — still "select, don't
 * type": the palette comes from the backend's catalog. */
export function ColorSwatches({ colors, selectedColor, onSelectColor }: ColorSwatchesProps) {
  return (
    <div role="radiogroup" aria-label="Color" className="flex flex-wrap gap-2">
      {colors.map((color) => {
        const isSelected = color === selectedColor;
        return (
          <button
            key={color}
            type="button"
            role="radio"
            aria-checked={isSelected}
            aria-label={GARMENT_COLOR_LABELS[color]}
            title={GARMENT_COLOR_LABELS[color]}
            onClick={() => onSelectColor(color)}
            style={{ backgroundColor: GARMENT_COLOR_SWATCHES[color] }}
            className={cn(
              "size-8 cursor-pointer rounded-full border border-black/15 ring-2 ring-transparent ring-offset-2 ring-offset-background transition-shadow",
              "hover:ring-border focus-visible:outline-none focus-visible:ring-ring",
              isSelected && "ring-primary hover:ring-primary",
            )}
          />
        );
      })}
    </div>
  );
}
