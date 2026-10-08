import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { Region } from "../../domain/entities/Region";
import { RegionOverlay } from "./RegionOverlay";

/** Regression test for a real bug: BODY's box naturally encloses nearly the
 * whole photo, so if regions render in detection order (BODY last), its
 * transparent button paints on top and intercepts every click meant for the
 * smaller face/hand/mouth/eyes regions underneath it — found while taking
 * screenshots against a real photo where the "Right hand" region became
 * unclickable once a BODY region was also detected. */
describe("RegionOverlay", () => {
  it("renders larger regions before smaller ones, so a small region inside a big one stays on top", () => {
    const regions: Region[] = [
      {
        regionId: "body",
        regionType: "body",
        boundingBox: { x: 0, y: 0, width: 800, height: 600 },
        confidence: 0.9,
      },
      {
        regionId: "hand",
        regionType: "right_hand",
        boundingBox: { x: 100, y: 100, width: 50, height: 50 },
        confidence: 0.9,
      },
    ];

    render(
      <RegionOverlay
        imageUrl="http://example.test/img.png"
        imageWidth={800}
        imageHeight={600}
        regions={regions}
        selectedRegionId={null}
        onSelectRegion={vi.fn()}
      />,
    );

    const buttons = screen.getAllByRole("button");
    const bodyIndex = buttons.findIndex((b) => b.getAttribute("aria-label") === "Body");
    const handIndex = buttons.findIndex((b) => b.getAttribute("aria-label") === "Right hand");

    expect(bodyIndex).toBeGreaterThanOrEqual(0);
    expect(handIndex).toBeGreaterThan(bodyIndex);
  });
});
