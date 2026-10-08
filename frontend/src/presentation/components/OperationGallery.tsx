import type { OperationCatalogEntry } from "../../application/ports/ImageApiPort";
import type { EditOperation } from "../../domain/types/EditOperation";
import { Card, CardContent } from "./ui/card";
import { cn } from "../lib/utils";

interface OperationGalleryProps {
  operations: OperationCatalogEntry[];
  selectedOperation: EditOperation | null;
  onSelectOperation: (operation: EditOperation) => void;
}

/** A visual grid of predefined operations (emoji + label) — never a plain
 * text list, per the product's "select, don't type" principle. */
export function OperationGallery({
  operations,
  selectedOperation,
  onSelectOperation,
}: OperationGalleryProps) {
  if (operations.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        This region doesn't have any operations available yet.
      </p>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {operations.map((op) => {
        const isSelected = op.operation === selectedOperation;
        return (
          <Card
            key={op.operation}
            role="button"
            tabIndex={0}
            aria-pressed={isSelected}
            onClick={() => onSelectOperation(op.operation)}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                onSelectOperation(op.operation);
              }
            }}
            className={cn(
              "cursor-pointer items-center p-4 text-center ring-2 ring-transparent transition-colors hover:ring-border",
              isSelected && "bg-primary/5 ring-primary",
            )}
          >
            <CardContent className="flex flex-col items-center gap-1.5 p-0">
              <span className="text-3xl" aria-hidden="true">
                {op.emoji}
              </span>
              <span className="text-sm font-medium">{op.label}</span>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
