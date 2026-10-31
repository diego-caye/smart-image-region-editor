import { useCallback } from "react";
import { analyzeImage } from "../../application/use-cases/analyzeImage";
import { confirmEdit as confirmEditUseCase } from "../../application/use-cases/confirmEdit";
import { currentImageDownloadUrl } from "../../application/use-cases/currentImageDownloadUrl";
import { discardEdit as discardEditUseCase } from "../../application/use-cases/discardEdit";
import { getEditHistory } from "../../application/use-cases/getEditHistory";
import { listOperationsForRegion } from "../../application/use-cases/listOperationsForRegion";
import { requestEdit as requestEditUseCase } from "../../application/use-cases/requestEdit";
import { undoLastEdit as undoLastEditUseCase } from "../../application/use-cases/undoLastEdit";
import { uploadImage } from "../../application/use-cases/uploadImage";
import type { EditOperation } from "../../domain/types/EditOperation";
import type { GarmentColor } from "../../domain/types/GarmentColor";
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

  // Best-effort: the history panel just keeps its previous contents if this
  // fails — never a reason to report the confirm/undo itself as failed.
  const refreshHistory = useCallback(
    async (imageId: string) => {
      try {
        const history = await getEditHistory(api, imageId);
        dispatch({ type: "HISTORY_SUCCESS", entries: history.entries, canUndo: history.canUndo });
      } catch {
        // keep the last known history
      }
    },
    [api, dispatch],
  );

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

  const selectColor = useCallback(
    (color: GarmentColor) => {
      dispatch({ type: "SELECT_COLOR", color });
    },
    [dispatch],
  );

  const requestEdit = useCallback(async () => {
    if (!state.image || !state.selectedRegionId || !state.selectedOperation) return;
    dispatch({ type: "EDIT_START" });
    try {
      const result = await requestEditUseCase(
        api,
        state.image.imageId,
        state.selectedRegionId,
        state.selectedOperation,
        state.selectedColor,
        (progress) => dispatch({ type: "EDIT_PROGRESS", progress }),
      );
      dispatch({
        type: "EDIT_SUCCESS",
        editId: result.editId,
        status: result.status,
        previewUrl: result.previewUrl,
        errorMessage: result.errorMessage,
      });
    } catch (error) {
      dispatch({ type: "EDIT_REQUEST_ERROR", message: messageFrom(error) });
    }
  }, [
    api,
    dispatch,
    state.image,
    state.selectedRegionId,
    state.selectedOperation,
    state.selectedColor,
  ]);

  const confirmEdit = useCallback(async () => {
    if (!state.editId) return;
    dispatch({ type: "CONFIRM_START" });
    try {
      const result = await confirmEditUseCase(api, state.editId);
      dispatch({ type: "CONFIRM_SUCCESS", finalUrl: result.finalUrl });
      if (state.image) await refreshHistory(state.image.imageId);
    } catch (error) {
      dispatch({ type: "CONFIRM_ERROR", message: messageFrom(error) });
    }
  }, [api, dispatch, state.editId, state.image, refreshHistory]);

  const undoLastEdit = useCallback(async () => {
    if (!state.image) return;
    dispatch({ type: "UNDO_START" });
    try {
      const result = await undoLastEditUseCase(api, state.image.imageId);
      dispatch({ type: "UNDO_SUCCESS", currentUrl: result.currentUrl });
      await refreshHistory(state.image.imageId);
    } catch (error) {
      dispatch({ type: "UNDO_ERROR", message: messageFrom(error) });
    }
  }, [api, dispatch, state.image, refreshHistory]);

  const downloadUrl = state.image ? currentImageDownloadUrl(api, state.image.imageId) : null;

  const discardEdit = useCallback(async () => {
    if (!state.editId) return;
    dispatch({ type: "DISCARD_START" });
    try {
      await discardEditUseCase(api, state.editId);
      dispatch({ type: "DISCARD_SUCCESS" });
    } catch (error) {
      dispatch({ type: "DISCARD_ERROR", message: messageFrom(error) });
    }
  }, [api, dispatch, state.editId]);

  return {
    ...state,
    upload,
    analyze,
    selectRegion,
    selectOperation,
    selectColor,
    requestEdit,
    confirmEdit,
    discardEdit,
    undoLastEdit,
    downloadUrl,
  };
}
