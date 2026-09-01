import { REGION_COLORS, REGION_LABELS } from "../../adapters/ui/regionPresentation";
import type { Region } from "../../domain/entities/Region";
import { cn } from "../lib/utils";

interface RegionOverlayProps {
  imageUrl: string;
  imageWidth: number;
  imageHeight: number;
  regions: Region[];
  selectedRegionId: string | null;
  onSelectRegion: (regionId: string) => void;
}

/** The image with detected regions drawn as clickable, colored boxes over
 * it — percentage-positioned against imageWidth/imageHeight so it stays
 * correctly aligned at any rendered size, no ResizeObserver needed. */
export function RegionOverlay({
  imageUrl,
  imageWidth,
  imageHeight,
  regions,
  selectedRegionId,
  onSelectRegion,
}: RegionOverlayProps) {
  return (
    <div
      className="relative mx-auto w-full max-w-xl overflow-hidden rounded-xl bg-muted shadow-md"
      style={{ aspectRatio: `${imageWidth} / ${imageHeight}` }}
    >
      <img src={imageUrl} alt="Imagen subida" className="block h-full w-full object-contain" />
      {regions.map((region) => {
        const isSelected = region.regionId === selectedRegionId;
        const color = REGION_COLORS[region.regionType];
        return (
          <button
            key={region.regionId}
            type="button"
            aria-pressed={isSelected}
            aria-label={REGION_LABELS[region.regionType]}
            onClick={() => onSelectRegion(region.regionId)}
            className={cn(
              "group absolute rounded-md border-2 bg-transparent transition hover:brightness-110",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-1",
            )}
            style={{
              left: `${(region.boundingBox.x / imageWidth) * 100}%`,
              top: `${(region.boundingBox.y / imageHeight) * 100}%`,
              width: `${(region.boundingBox.width / imageWidth) * 100}%`,
              height: `${(region.boundingBox.height / imageHeight) * 100}%`,
              borderColor: color,
              boxShadow: isSelected ? `0 0 0 3px ${color}66` : "none",
            }}
          >
            <span
              className="pointer-events-none absolute -top-6 left-0 whitespace-nowrap rounded px-1.5 py-0.5 text-xs font-medium text-white opacity-0 transition-opacity group-hover:opacity-100"
              style={{ backgroundColor: color, opacity: isSelected ? 1 : undefined }}
            >
              {REGION_LABELS[region.regionType]}
            </span>
          </button>
        );
      })}
    </div>
  );
}
