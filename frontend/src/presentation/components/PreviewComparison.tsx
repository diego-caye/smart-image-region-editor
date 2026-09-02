import { Button } from "./ui/button";

interface PreviewComparisonProps {
  beforeUrl: string;
  afterUrl: string;
  onAccept: () => void;
  onDiscard: () => void;
  isConfirming: boolean;
  isDiscarding: boolean;
}

/** Original | Result, side by side, with Accept/Discard — nothing is
 * applied to the session's image until the user explicitly accepts. */
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
      <div className="grid grid-cols-2 gap-3">
        <figure className="flex flex-col gap-1.5">
          <img src={beforeUrl} alt="Antes" className="rounded-lg border border-border" />
          <figcaption className="text-center text-xs text-muted-foreground">Antes</figcaption>
        </figure>
        <figure className="flex flex-col gap-1.5">
          <img src={afterUrl} alt="Después" className="rounded-lg border border-border" />
          <figcaption className="text-center text-xs text-muted-foreground">Después</figcaption>
        </figure>
      </div>
      <div className="flex gap-2">
        <Button onClick={onAccept} disabled={busy}>
          {isConfirming ? "Aceptando…" : "Aceptar"}
        </Button>
        <Button variant="outline" onClick={onDiscard} disabled={busy}>
          {isDiscarding ? "Descartando…" : "Descartar"}
        </Button>
      </div>
    </div>
  );
}
