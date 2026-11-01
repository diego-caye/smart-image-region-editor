import { useState } from "react";

interface BeforeAfterSliderProps {
  beforeUrl: string;
  afterUrl: string;
  beforeLabel?: string;
  afterLabel?: string;
}

/** Before | After on the same photo, split by a draggable divider. The
 * edits are local to a region, so comparing in place shows exactly what
 * changed (and that nothing else did) far better than two images side by
 * side. The labels double as the images' alt text. */
export function BeforeAfterSlider({
  beforeUrl,
  afterUrl,
  beforeLabel = "Before",
  afterLabel = "After",
}: BeforeAfterSliderProps) {
  const [position, setPosition] = useState(50);

  return (
    <div className="relative select-none overflow-hidden rounded-lg border border-border">
      <img src={beforeUrl} alt={beforeLabel} className="block w-full" draggable={false} />
      <img
        src={afterUrl}
        alt={afterLabel}
        className="absolute inset-0 h-full w-full"
        style={{ clipPath: `inset(0 0 0 ${position}%)` }}
        draggable={false}
      />
      <span className="pointer-events-none absolute left-2 top-2 rounded bg-black/60 px-1.5 py-0.5 text-xs font-medium text-white">
        {beforeLabel}
      </span>
      <span className="pointer-events-none absolute right-2 top-2 rounded bg-black/60 px-1.5 py-0.5 text-xs font-medium text-white">
        {afterLabel}
      </span>
      {/* A native range input over the whole image: mouse, touch and
          arrow-key support for free; it's invisible, the divider below
          is what's drawn. */}
      <input
        type="range"
        min={0}
        max={100}
        value={position}
        onChange={(event) => setPosition(Number(event.target.value))}
        aria-label={`Compare ${beforeLabel.toLowerCase()} and ${afterLabel.toLowerCase()}`}
        className="peer absolute inset-0 h-full w-full cursor-ew-resize opacity-0"
      />
      {/* peer-focus-visible only reaches the input's siblings, so it's
          set here and passed down to the handle with *: — keyboard users
          see where focus is. */}
      <div
        className="pointer-events-none absolute inset-y-0 w-0.5 -translate-x-1/2 bg-white shadow-[0_0_0_1px_rgba(0,0,0,0.25)] peer-focus-visible:*:ring-2"
        style={{ left: `${position}%` }}
      >
        <div className="absolute left-1/2 top-1/2 flex h-8 w-8 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full bg-white text-xs text-foreground shadow-md ring-primary">
          ⇆
        </div>
      </div>
    </div>
  );
}
