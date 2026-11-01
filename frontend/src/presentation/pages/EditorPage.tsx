import { REGION_LABELS } from "../../adapters/ui/regionPresentation";
import { GARMENT_COLOR_LABELS } from "../../adapters/ui/garmentColorPresentation";
import { ColorSwatches } from "../components/ColorSwatches";
import { EditHistoryPanel } from "../components/EditHistoryPanel";
import { EditProgressBar } from "../components/EditProgressBar";
import { ImageUploader } from "../components/ImageUploader";
import { OperationGallery } from "../components/OperationGallery";
import { PreviewComparison } from "../components/PreviewComparison";
import { RegionOverlay } from "../components/RegionOverlay";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Skeleton } from "../components/ui/skeleton";
import { useEditSession } from "../hooks/useEditSession";

export function EditorPage() {
  const {
    status,
    image,
    errorMessage,
    currentImageUrl,
    analysisStatus,
    analysisError,
    regions,
    selectedRegionId,
    operationsStatus,
    operationsError,
    operations,
    selectedOperation,
    selectedColor,
    editGenerationStatus,
    editProgress,
    editError,
    editBeforeUrl,
    previewUrl,
    editConfirmStatus,
    history,
    canUndo,
    isUndoing,
    undoError,
    downloadUrl,
    upload,
    analyze,
    selectRegion,
    selectOperation,
    selectColor,
    requestEdit,
    confirmEdit,
    discardEdit,
    undoLastEdit,
  } = useEditSession();

  const selectedRegion = regions.find((r) => r.regionId === selectedRegionId) ?? null;
  const selectedOperationEntry = operations.find((op) => op.operation === selectedOperation) ?? null;

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-6 px-6 py-10">
      <div>
        <h1 className="text-2xl font-semibold">Smart Image Region Editor</h1>
        <p className="text-sm text-muted-foreground">
          Upload a photo, pick a detected region, and a visual transformation.
        </p>
      </div>

      {status !== "ready" && (
        <ImageUploader onFileSelected={upload} isUploading={status === "uploading"} />
      )}

      {status === "error" && errorMessage && (
        <p role="alert" className="rounded-lg bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {errorMessage}
        </p>
      )}

      {image && currentImageUrl && (
        <Card>
          <CardHeader>
            <CardTitle>1. Image</CardTitle>
            <CardDescription>
              {image.width}×{image.height}px
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <RegionOverlay
              imageUrl={currentImageUrl}
              imageWidth={image.width}
              imageHeight={image.height}
              regions={regions}
              selectedRegionId={selectedRegionId}
              onSelectRegion={selectRegion}
            />

            {analysisStatus === "idle" && (
              <Button onClick={analyze} className="self-start">
                Analyze image
              </Button>
            )}
            {analysisStatus === "analyzing" && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Skeleton className="h-4 w-4 rounded-full" />
                Detecting regions…
              </div>
            )}
            {analysisStatus === "error" && (
              <div className="flex flex-col gap-2">
                <p role="alert" className="text-sm text-destructive">
                  {analysisError}
                </p>
                <Button onClick={analyze} variant="outline" className="self-start">
                  Retry
                </Button>
              </div>
            )}
            {analysisStatus === "ready" && (
              <p className="text-sm text-muted-foreground">
                {regions.length > 0
                  ? "Tap a highlighted region in the image to edit it."
                  : "No regions were detected in this image."}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {image && downloadUrl && (
        <Card>
          <CardHeader>
            <CardTitle>History</CardTitle>
            <CardDescription>Edits stack on top of each other; undo goes back one.</CardDescription>
          </CardHeader>
          <CardContent>
            <EditHistoryPanel
              entries={history}
              canUndo={canUndo}
              isUndoing={isUndoing}
              undoError={undoError}
              downloadUrl={downloadUrl}
              originalUrl={image.url}
              currentUrl={currentImageUrl ?? image.url}
              onUndo={undoLastEdit}
            />
          </CardContent>
        </Card>
      )}

      {selectedRegion && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              2. Choose a transformation
              <Badge variant="secondary">{REGION_LABELS[selectedRegion.regionType]}</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {operationsStatus === "loading" && (
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {Array.from({ length: 4 }).map((_, i) => (
                  <Skeleton key={i} className="h-24 rounded-xl" />
                ))}
              </div>
            )}
            {operationsStatus === "error" && (
              <p role="alert" className="text-sm text-destructive">
                {operationsError}
              </p>
            )}
            {operationsStatus === "ready" && (
              <OperationGallery
                operations={operations}
                selectedOperation={selectedOperation}
                onSelectOperation={selectOperation}
              />
            )}
            {selectedOperationEntry && selectedOperationEntry.colors.length > 0 && (
              <div className="mt-4 flex flex-col gap-2">
                <span className="text-sm font-medium">Color</span>
                <ColorSwatches
                  colors={selectedOperationEntry.colors}
                  selectedColor={selectedColor}
                  onSelectColor={selectColor}
                />
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {selectedRegion && selectedOperationEntry && (
        <Card>
          <CardHeader>
            <CardTitle>3. Preview</CardTitle>
            <CardDescription>
              {REGION_LABELS[selectedRegion.regionType]} → {selectedOperationEntry.label}
              {selectedColor && ` · ${GARMENT_COLOR_LABELS[selectedColor]}`}
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {editGenerationStatus === "idle" && (
              <Button onClick={requestEdit} className="self-start">
                Generate preview
              </Button>
            )}
            {editGenerationStatus === "generating" && <EditProgressBar progress={editProgress} />}
            {editGenerationStatus === "error" && (
              <div className="flex flex-col gap-2">
                <p role="alert" className="text-sm text-destructive">
                  {editError}
                </p>
                <Button onClick={requestEdit} variant="outline" className="self-start">
                  Retry
                </Button>
              </div>
            )}
            {editGenerationStatus === "ready" && previewUrl && editBeforeUrl && (
              <PreviewComparison
                beforeUrl={editBeforeUrl}
                afterUrl={previewUrl}
                onAccept={confirmEdit}
                onDiscard={discardEdit}
                isConfirming={editConfirmStatus === "confirming"}
                isDiscarding={editConfirmStatus === "discarding"}
              />
            )}
          </CardContent>
        </Card>
      )}
    </main>
  );
}
