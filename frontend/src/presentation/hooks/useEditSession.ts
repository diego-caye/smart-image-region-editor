import { useCallback } from "react";
import { analyzeImage } from "../../application/use-cases/analyzeImage";
import { listOperationsForRegion } from "../../application/use-cases/listOperationsForRegion";
import { uploadImage } from "../../application/use-cases/uploadImage";
import type { EditOperation } from "../../domain/types/EditOperation";
import { useEditSessionContext } from "../../infrastructure/state/EditSessionContext";

function messageFrom(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong";
}

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
        dispatch({ type: "UPLOAD_ERROR", message: messageFrom(error) });
      }
    },
    [api, dispatch],
  );

  const analyze = useCallback(async () => {
    if (!state.image) return;
    dispatch({ type: "ANALYZE_START" });
    try {
      const regions = await analyzeImage(api, state.image.imageId);
      dispatch({ type: "ANALYZE_SUCCESS", regions });
    } catch (error) {
      dispatch({ type: "ANALYZE_ERROR", message: messageFrom(error) });
    }
  }, [api, dispatch, state.image]);

  const selectRegion = useCallback(
    async (regionId: string) => {
      dispatch({ type: "SELECT_REGION", regionId });
      const region = state.regions.find((r) => r.regionId === regionId);
      if (!region) return;

      dispatch({ type: "OPERATIONS_START" });
      try {
        const operations = await listOperationsForRegion(api, region.regionType);
        dispatch({ type: "OPERATIONS_SUCCESS", operations });
      } catch (error) {
        dispatch({ type: "OPERATIONS_ERROR", message: messageFrom(error) });
      }
    },
    [api, dispatch, state.regions],
  );

  const selectOperation = useCallback(
    (operation: EditOperation) => {
      dispatch({ type: "SELECT_OPERATION", operation });
    },
    [dispatch],
  );

  return { ...state, upload, analyze, selectRegion, selectOperation };
}
