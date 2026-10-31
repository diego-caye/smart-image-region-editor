import { useState } from "react";
import { Button } from "./ui/button";

interface PreviewComparisonProps {
  beforeUrl: string;
  afterUrl: string;
  onAccept: () => void;
  onDiscard: () => void;
  isConfirming: boolean;
  isDiscarding: boolean;
}

/** Before | After on the same photo, split by a draggable divider, with
 * Accept/Discard — nothing is applied to the session's image until the
 * user explicitly accepts. The edit is local to one region, so comparing
 * it in place shows exactly what changed (and that nothing else did) far
 * better than two images side by side. */
export function PreviewComparison({
  beforeUrl,
  afterUrl,
  onAccept,
  onDiscard,
  isConfirming,
  isDiscarding,
}: PreviewComparisonProps) {
  const [position, setPosition] = useState(50);
  const busy = isConfirming || isDiscarding;

  return (
    <div className="flex flex-col gap-4">
      <div className="relative select-none overflow-hidden rounded-lg border border-border">
        <img src={beforeUrl} alt="Before" className="block w-full" draggable={false} />
        <img
          src={afterUrl}
          alt="After"
          className="absolute inset-0 h-full w-full"
          style={{ clipPath: `inset(0 0 0 ${position}%)` }}
          draggable={false}
        />
        <span className="pointer-events-none absolute left-2 top-2 rounded bg-black/60 px-1.5 py-0.5 text-xs font-medium text-white">
          Before
        </span>
        <span className="pointer-events-none absolute right-2 top-2 rounded bg-black/60 px-1.5 py-0.5 text-xs font-medium text-white">
          After
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
          aria-label="Compare before and after"
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
      <div className="flex gap-2">
        <Button onClick={onAccept} disabled={busy}>
          {isConfirming ? "Accepting…" : "Accept"}
        </Button>
        <Button variant="outline" onClick={onDiscard} disabled={busy}>
          {isDiscarding ? "Discarding…" : "Discard"}
        </Button>
      </div>
    </div>
  );
}
