import { BeforeAfterSlider } from "./BeforeAfterSlider";
import { Button } from "./ui/button";

interface PreviewComparisonProps {
  beforeUrl: string;
  afterUrl: string;
  onAccept: () => void;
  onDiscard: () => void;
  isConfirming: boolean;
  isDiscarding: boolean;
}

/** The preview against the current image, with Accept/Discard — nothing
 * is applied to the session's image until the user explicitly accepts. */
export function PreviewComparison({
  beforeUrl,
  afterUrl,
  onAccept,
  onDiscard,
  isConfirming,
  isDiscarding,
}: PreviewComparisonProps) {
  const busy = isConfirming || isDiscarding;

  return (
    <div className="flex flex-col gap-4">
      <BeforeAfterSlider beforeUrl={beforeUrl} afterUrl={afterUrl} />
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
