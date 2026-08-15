/** Absolute pixel coordinates in the *original* image's own dimensions —
 * presentation/components/RegionOverlay is responsible for scaling this to
 * whatever size the image is actually rendered at. */
export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}
