import type { EditOperation } from "./EditOperation";
import type { GarmentColor } from "./GarmentColor";
import type { RegionType } from "./RegionType";

/** One edit that was applied to the image — and possibly undone since. */
export interface EditHistoryEntry {
  editId: string;
  regionType: RegionType | null;
  operation: EditOperation;
  label: string;
  emoji: string;
  color: GarmentColor | null;
  status: "confirmed" | "reverted";
}

export interface EditHistory {
  entries: EditHistoryEntry[]; // oldest first
  canUndo: boolean;
}
