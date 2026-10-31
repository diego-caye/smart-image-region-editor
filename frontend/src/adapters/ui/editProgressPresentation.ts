import type { EditProgress, EditStage } from "../../domain/types/EditProgress";

/**
 * Edit stage -> what the user reads. Presentation concern, kept apart from
 * the pure EditProgress type (same split as regionPresentation.ts).
 */
const STAGE_LABELS: Record<EditStage, string> = {
  segmenting: "Masking the region",
  reading_instruction: "Reading the instruction",
  // The longest wait: model weights load here, before the first step.
  loading_model: "Loading the editing model",
  generating: "Generating",
  decoding: "Decoding the image",
  compositing: "Blending it into the photo",
  done: "Done",
};

export function progressLabel(progress: EditProgress | null): string {
  if (!progress) return "Starting…";
  if (progress.stage === "generating" && progress.step != null && progress.steps != null) {
    return `Generating — step ${progress.step} of ${progress.steps}`;
  }
  return STAGE_LABELS[progress.stage];
}
