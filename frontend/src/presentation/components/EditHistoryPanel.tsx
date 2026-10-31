import { REGION_LABELS } from "../../adapters/ui/regionPresentation";
import { GARMENT_COLOR_LABELS } from "../../adapters/ui/garmentColorPresentation";
import type { EditHistoryEntry } from "../../domain/types/EditHistory";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { cn } from "../lib/utils";

interface EditHistoryPanelProps {
  entries: EditHistoryEntry[];
  canUndo: boolean;
  isUndoing: boolean;
  undoError: string | null;
  downloadUrl: string;
  onUndo: () => void;
}

/** What has been applied to the image so far, with Undo (one step at a
 * time, back to the original) and a download of the image as it is now. */
export function EditHistoryPanel({
  entries,
  canUndo,
  isUndoing,
  undoError,
  downloadUrl,
  onUndo,
}: EditHistoryPanelProps) {
  return (
    <div className="flex flex-col gap-3">
      {entries.length === 0 ? (
        <p className="text-sm text-muted-foreground">No edits applied yet.</p>
      ) : (
        <ol aria-label="Applied edits" className="flex flex-col gap-1.5">
          {entries.map((entry, index) => {
            const reverted = entry.status === "reverted";
            const region = entry.regionType ? REGION_LABELS[entry.regionType] : "Region";
            const color = entry.color ? ` · ${GARMENT_COLOR_LABELS[entry.color]}` : "";
            return (
              <li key={entry.editId} className="flex items-center gap-2 text-sm">
                <span className="w-5 text-right text-muted-foreground">{index + 1}.</span>
                <span aria-hidden="true">{entry.emoji}</span>
                <span className={cn(reverted && "text-muted-foreground line-through")}>
                  {region} → {entry.label}
                  {color}
                </span>
                {reverted && <Badge variant="secondary">Undone</Badge>}
              </li>
            );
          })}
        </ol>
      )}
      {undoError && (
        <p role="alert" className="text-sm text-destructive">
          {undoError}
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        <Button variant="outline" onClick={onUndo} disabled={!canUndo || isUndoing}>
          {isUndoing ? "Undoing…" : "Undo last edit"}
        </Button>
        <Button asChild>
          <a href={downloadUrl} download>
            Download image
          </a>
        </Button>
      </div>
    </div>
  );
}
