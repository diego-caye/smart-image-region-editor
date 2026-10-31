/**
 * Mirrors backend app.application.dto.edit_progress (EditStage /
 * EditProgress). Display text lives in adapters/ui/editProgressPresentation.ts,
 * not here — this stays a pure type.
 */
export type EditStage =
  | "segmenting"
  | "reading_instruction"
  | "loading_model"
  | "generating"
  | "decoding"
  | "compositing"
  | "done";

export interface EditProgress {
  stage: EditStage;
  /** 0-1, only moves forward over a run. */
  fraction: number;
  /** Sampling step, only while generating. */
  step: number | null;
  steps: number | null;
}
