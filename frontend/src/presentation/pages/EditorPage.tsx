import { REGION_LABELS } from "../../adapters/ui/regionPresentation";
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
    editGenerationStatus,
    editError,
    editBeforeUrl,
    previewUrl,
    editConfirmStatus,
    upload,
    analyze,
    selectRegion,
    selectOperation,
    requestEdit,
    confirmEdit,
    discardEdit,
  } = useEditSession();

  const selectedRegion = regions.find((r) => r.regionId === selectedRegionId) ?? null;
  const selectedOperationEntry = operations.find((op) => op.operation === selectedOperation) ?? null;

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-6 px-6 py-10">
      <div>
        <h1 className="text-2xl font-semibold">Smart Image Region Editor</h1>
        <p className="text-sm text-muted-foreground">
          Sube una foto, elige una región detectada y una transformación visual.
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
            <CardTitle>1. Imagen</CardTitle>
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
                Analizar imagen
              </Button>
            )}
            {analysisStatus === "analyzing" && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Skeleton className="h-4 w-4 rounded-full" />
                Detectando cara y manos…
              </div>
            )}
            {analysisStatus === "error" && (
              <div className="flex flex-col gap-2">
                <p role="alert" className="text-sm text-destructive">
                  {analysisError}
                </p>
                <Button onClick={analyze} variant="outline" className="self-start">
                  Reintentar
                </Button>
              </div>
            )}
            {analysisStatus === "ready" && (
              <p className="text-sm text-muted-foreground">
                {regions.length > 0
                  ? "Toca una región resaltada en la imagen para editarla."
                  : "No se detectó ninguna región en esta imagen."}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {selectedRegion && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              2. Elige una transformación
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
          </CardContent>
        </Card>
      )}

      {selectedRegion && selectedOperationEntry && (
        <Card>
          <CardHeader>
            <CardTitle>3. Vista previa</CardTitle>
            <CardDescription>
              {REGION_LABELS[selectedRegion.regionType]} → {selectedOperationEntry.label}
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {editGenerationStatus === "idle" && (
              <Button onClick={requestEdit} className="self-start">
                Generar vista previa
              </Button>
            )}
            {editGenerationStatus === "generating" && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Skeleton className="h-4 w-4 rounded-full" />
                Generando con Qwen (vía ComfyUI)… esto puede tardar unos 20-30 segundos.
              </div>
            )}
            {editGenerationStatus === "error" && (
              <div className="flex flex-col gap-2">
                <p role="alert" className="text-sm text-destructive">
                  {editError}
                </p>
                <Button onClick={requestEdit} variant="outline" className="self-start">
                  Reintentar
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
