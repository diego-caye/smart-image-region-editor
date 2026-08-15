import { useCallback } from "react";
import { uploadImage } from "../../application/use-cases/uploadImage";
import { useEditSessionContext } from "../../infrastructure/state/EditSessionContext";

/**
 * The only thing presentation/components are allowed to call. It never
 * touches fetch/endpoints itself — it goes hook -> application use-case ->
 * port -> adapter, same boundary the backend enforces.
 */
export function useEditSession() {
  const { state, dispatch, api } = useEditSessionContext();

  const upload = useCallback(
    async (file: File) => {
      dispatch({ type: "UPLOAD_START" });
      try {
        const image = await uploadImage(api, file);
        dispatch({ type: "UPLOAD_SUCCESS", image });
      } catch (error) {
        dispatch({
          type: "UPLOAD_ERROR",
          message: error instanceof Error ? error.message : "Upload failed",
        });
      }
    },
    [api, dispatch],
  );

  return { ...state, upload };
}
