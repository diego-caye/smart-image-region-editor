import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { PreviewComparison } from "./PreviewComparison";

function renderComparison() {
  render(
    <PreviewComparison
      beforeUrl="http://example.test/before.png"
      afterUrl="http://example.test/after.png"
      onAccept={vi.fn()}
      onDiscard={vi.fn()}
      isConfirming={false}
      isDiscarding={false}
    />,
  );
}

describe("PreviewComparison", () => {
  it("starts split down the middle", () => {
    renderComparison();
    expect(screen.getByAltText("After")).toHaveStyle({ clipPath: "inset(0 0 0 50%)" });
    expect(screen.getByRole("slider", { name: "Compare before and after" })).toHaveValue("50");
  });

  it("moving the divider reveals more of the edit", () => {
    renderComparison();
    fireEvent.change(screen.getByRole("slider"), { target: { value: "20" } });
    // the "after" image covers everything right of the divider
    expect(screen.getByAltText("After")).toHaveStyle({ clipPath: "inset(0 0 0 20%)" });
  });
});
