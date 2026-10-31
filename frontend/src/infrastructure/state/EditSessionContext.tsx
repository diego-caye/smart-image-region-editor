import { createContext, useContext, useMemo, useReducer, type Dispatch, type ReactNode } from "react";
import { HttpImageApi } from "../../adapters/http/HttpImageApi";
import type { ImageApiPort, OperationCatalogEntry } from "../../application/ports/ImageApiPort";
import type { Region } from "../../domain/entities/Region";
import type { UploadedImage } from "../../domain/entities/UploadedImage";
import type { EditOperation } from "../../domain/types/EditOperation";
import type { EditProgress } from "../../domain/types/EditProgress";
import type { GarmentColor } from "../../domain/types/GarmentColor";

export type UploadStatus = "idle" | "uploading" | "ready" | "error";
export type AnalysisStatus = "idle" | "analyzing" | "ready" | "error";
export type OperationsStatus = "idle" | "loading" | "ready" | "error";
export type EditGenerationStatus = "idle" | "generating" | "ready" | "error";
export type EditConfirmStatus = "idle" | "confirming" | "discarding" | "error";

export interface EditSessionState {
  status: UploadStatus;
  image: UploadedImage | null;
  errorMessage: string | null;

  // The image regions/edits are shown against and applied on top of —
  // starts as the original upload, advances to each confirmed edit's
  // result so a second edit builds on the first instead of overwriting it.
  currentImageUrl: string | null;

  analysisStatus: AnalysisStatus;
  analysisError: string | null;
  regions: Region[];

  selectedRegionId: string | null;
  operationsStatus: OperationsStatus;
  operationsError: string | null;
  operations: OperationCatalogEntry[];

  selectedOperation: EditOperation | null;
  // Preselected to the palette's first color when a garment is picked, so
  // "Generate preview" always has everything it needs.
  selectedColor: GarmentColor | null;

  editId: string | null;
  editGenerationStatus: EditGenerationStatus;
  // Null until the backend reports the first stage of a running edit.
  editProgress: EditProgress | null;
  editError: string | null;
  editBeforeUrl: string | null;
  previewUrl: string | null;
  editConfirmStatus: EditConfirmStatus;
}

export type EditSessionAction =
  | { type: "UPLOAD_START" }
  | { type: "UPLOAD_SUCCESS"; image: UploadedImage }
  | { type: "UPLOAD_ERROR"; message: string }
  | { type: "ANALYZE_START" }
  | { type: "ANALYZE_SUCCESS"; regions: Region[] }
  | { type: "ANALYZE_ERROR"; message: string }
  | { type: "SELECT_REGION"; regionId: string }
  | { type: "OPERATIONS_START" }
  | { type: "OPERATIONS_SUCCESS"; operations: OperationCatalogEntry[] }
  | { type: "OPERATIONS_ERROR"; message: string }
  | { type: "SELECT_OPERATION"; operation: EditOperation }
  | { type: "SELECT_COLOR"; color: GarmentColor }
  | { type: "EDIT_START" }
  | { type: "EDIT_PROGRESS"; progress: EditProgress }
  | {
      type: "EDIT_SUCCESS";
      editId: string;
      status: "preview_ready" | "failed";
      previewUrl: string | null;
      errorMessage: string | null;
    }
  | { type: "EDIT_REQUEST_ERROR"; message: string }
  | { type: "CONFIRM_START" }
  | { type: "CONFIRM_SUCCESS"; finalUrl: string }
  | { type: "CONFIRM_ERROR"; message: string }
  | { type: "DISCARD_START" }
  | { type: "DISCARD_SUCCESS" }
  | { type: "DISCARD_ERROR"; message: string };

const initialState: EditSessionState = {
  status: "idle",
  image: null,
  errorMessage: null,
  currentImageUrl: null,
  analysisStatus: "idle",
  analysisError: null,
  regions: [],
  selectedRegionId: null,
  operationsStatus: "idle",
  operationsError: null,
  operations: [],
  selectedOperation: null,
  selectedColor: null,
  editId: null,
  editGenerationStatus: "idle",
  editProgress: null,
  editError: null,
  editBeforeUrl: null,
  previewUrl: null,
  editConfirmStatus: "idle",
};

const clearedEditState = {
  editId: null,
  editGenerationStatus: "idle" as const,
  editProgress: null,
  editError: null,
  editBeforeUrl: null,
  previewUrl: null,
  editConfirmStatus: "idle" as const,
};

function reducer(state: EditSessionState, action: EditSessionAction): EditSessionState {
  switch (action.type) {
    case "UPLOAD_START":
      return { ...initialState, status: "uploading" };
    case "UPLOAD_SUCCESS":
      return {
        ...initialState,
        status: "ready",
        image: action.image,
        currentImageUrl: action.image.url,
      };
    case "UPLOAD_ERROR":
      return { ...state, status: "error", errorMessage: action.message };

    case "ANALYZE_START":
      return { ...state, analysisStatus: "analyzing", analysisError: null };
    case "ANALYZE_SUCCESS":
      return { ...state, analysisStatus: "ready", regions: action.regions };
    case "ANALYZE_ERROR":
      return { ...state, analysisStatus: "error", analysisError: action.message };

    // Selecting a (possibly different) region always clears whatever
    // operation catalog/selection/edit belonged to the previous one.
    case "SELECT_REGION":
      return {
        ...state,
        selectedRegionId: action.regionId,
        operationsStatus: "idle",
        operationsError: null,
        operations: [],
        selectedOperation: null,
        selectedColor: null,
        ...clearedEditState,
      };
    case "OPERATIONS_START":
      return { ...state, operationsStatus: "loading", operationsError: null };
    case "OPERATIONS_SUCCESS":
      return { ...state, operationsStatus: "ready", operations: action.operations };
    case "OPERATIONS_ERROR":
      return { ...state, operationsStatus: "error", operationsError: action.message };

    // Picking a different operation (or color) invalidates any preview
    // generated for the previous one.
    case "SELECT_OPERATION": {
      const entry = state.operations.find((op) => op.operation === action.operation);
      return {
        ...state,
        selectedOperation: action.operation,
        selectedColor: entry?.colors[0] ?? null,
        ...clearedEditState,
      };
    }
    case "SELECT_COLOR":
      return { ...state, selectedColor: action.color, ...clearedEditState };

    case "EDIT_START":
      return {
        ...state,
        editGenerationStatus: "generating",
        editProgress: null,
        editError: null,
        editBeforeUrl: state.currentImageUrl,
        previewUrl: null,
        editId: null,
      };
    case "EDIT_PROGRESS":
      // A late report must not bring back a bar for an edit that already
      // finished or was replaced.
      return state.editGenerationStatus === "generating"
        ? { ...state, editProgress: action.progress }
        : state;
    case "EDIT_SUCCESS":
      return {
        ...state,
        editId: action.editId,
        editGenerationStatus: action.status === "preview_ready" ? "ready" : "error",
        editProgress: null,
        editError: action.status === "failed" ? action.errorMessage : null,
        previewUrl: action.previewUrl,
      };
    case "EDIT_REQUEST_ERROR":
      return {
        ...state,
        editGenerationStatus: "error",
        editProgress: null,
        editError: action.message,
      };

    case "CONFIRM_START":
      return { ...state, editConfirmStatus: "confirming" };
    case "CONFIRM_SUCCESS":
      return {
        ...state,
        currentImageUrl: action.finalUrl,
        selectedRegionId: null,
        operationsStatus: "idle",
        operations: [],
        selectedOperation: null,
        selectedColor: null,
        ...clearedEditState,
      };
    case "CONFIRM_ERROR":
      return { ...state, editConfirmStatus: "error", editError: action.message };

    case "DISCARD_START":
      return { ...state, editConfirmStatus: "discarding" };
    case "DISCARD_SUCCESS":
      // Keep the region/operation catalog so the user can immediately try
      // a different operation on the same region.
      return { ...state, ...clearedEditState };
    case "DISCARD_ERROR":
      return { ...state, editConfirmStatus: "error", editError: action.message };

    default:
      return state;
  }
}

interface EditSessionContextValue {
  state: EditSessionState;
  dispatch: Dispatch<EditSessionAction>;
  api: ImageApiPort;
}

const EditSessionContext = createContext<EditSessionContextValue | null>(null);

/** The wizard's shared state. A linear upload -> analyze -> select region ->
 * select operation -> generate/accept flow doesn't need Redux/Zustand — a
 * Context + reducer is enough, and it's the only piece of
 * frontend/infrastructure that presentation hooks reach into. `api`
 * defaults to the real HttpImageApi but can be swapped (tests, storybook)
 * via the prop. */
export function EditSessionProvider({
  children,
  api = new HttpImageApi(),
}: {
  children: ReactNode;
  api?: ImageApiPort;
}) {
  const [state, dispatch] = useReducer(reducer, initialState);
  const value = useMemo(() => ({ state, dispatch, api }), [state, api]);
  return <EditSessionContext.Provider value={value}>{children}</EditSessionContext.Provider>;
}

export function useEditSessionContext(): EditSessionContextValue {
  const context = useContext(EditSessionContext);
  if (!context) {
    throw new Error("useEditSessionContext must be used within an EditSessionProvider");
  }
  return context;
}
