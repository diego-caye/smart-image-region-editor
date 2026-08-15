import { createContext, useContext, useMemo, useReducer, type Dispatch, type ReactNode } from "react";
import { HttpImageApi } from "../../adapters/http/HttpImageApi";
import type { ImageApiPort } from "../../application/ports/ImageApiPort";
import type { UploadedImage } from "../../domain/entities/UploadedImage";

export type UploadStatus = "idle" | "uploading" | "ready" | "error";

export interface EditSessionState {
  status: UploadStatus;
  image: UploadedImage | null;
  errorMessage: string | null;
}

export type EditSessionAction =
  | { type: "UPLOAD_START" }
  | { type: "UPLOAD_SUCCESS"; image: UploadedImage }
  | { type: "UPLOAD_ERROR"; message: string };

const initialState: EditSessionState = { status: "idle", image: null, errorMessage: null };

function reducer(state: EditSessionState, action: EditSessionAction): EditSessionState {
  switch (action.type) {
    case "UPLOAD_START":
      return { ...state, status: "uploading", errorMessage: null };
    case "UPLOAD_SUCCESS":
      return { status: "ready", image: action.image, errorMessage: null };
    case "UPLOAD_ERROR":
      return { ...state, status: "error", errorMessage: action.message };
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

/** The wizard's shared state. A linear upload -> analyze -> select ->
 * preview flow doesn't need Redux/Zustand — a Context + reducer is enough,
 * and it's the only piece of frontend/infrastructure that presentation
 * hooks reach into. `api` defaults to the real HttpImageApi but can be
 * swapped (tests, storybook) via the prop. */
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
