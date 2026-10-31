import { useEffect, useState } from "react";
import { progressLabel } from "../../adapters/ui/editProgressPresentation";
import type { EditProgress } from "../../domain/types/EditProgress";

interface EditProgressBarProps {
  progress: EditProgress | null;
}

/** What's happening while an edit runs (~1 min), plus seconds elapsed —
 * the stage moves the bar in steps, so the counter is what shows it's
 * alive during the long model load. Elapsed time counts from mount: the
 * parent mounts this exactly when generation starts. */
export function EditProgressBar({ progress }: EditProgressBarProps) {
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    const startedAt = Date.now();
    const timer = setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - startedAt) / 1000));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const percent = Math.round((progress?.fraction ?? 0) * 100);
  const label = progressLabel(progress);

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-baseline justify-between text-sm">
        <span className="font-medium">{label}</span>
        <span className="tabular-nums text-muted-foreground">{elapsedSeconds}s</span>
      </div>
      <div
        role="progressbar"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent}
        className="h-2 w-full overflow-hidden rounded-full bg-muted"
      >
        <div
          className="h-full rounded-full bg-primary transition-[width] duration-500 ease-out"
          style={{ width: `${Math.max(percent, 3)}%` }}
        />
      </div>
    </div>
  );
}
