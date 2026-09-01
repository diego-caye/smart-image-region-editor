import { REGION_LABELS } from "../../adapters/ui/regionPresentation";
import { ImageUploader } from "../components/ImageUploader";
import { OperationGallery } from "../components/OperationGallery";
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
    analysisStatus,
    analysisError,
    regions,
    selectedRegionId,
    operationsStatus,
    operationsError,
    operations,
    selectedOperation,
    upload,
    analyze,
    selectRegion,
    selectOperation,
  } = useEditSession();

  const selectedRegion = regions.find((r) => r.regionId === selectedRegionId) ?? null;

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

      {image && (
        <Card>
          <CardHeader>
            <CardTitle>1. Imagen</CardTitle>
            <CardDescription>
              {image.width}×{image.height}px
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <RegionOverlay
              imageUrl={image.url}
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

      {selectedOperation && selectedRegion && (
        <Card>
          <CardHeader>
            <CardTitle>3. Vista previa</CardTitle>
            <CardDescription>
              {REGION_LABELS[selectedRegion.regionType]} →{" "}
              {operations.find((op) => op.operation === selectedOperation)?.label}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              La edición localizada con Qwen (vía ComfyUI) todavía no está conectada — esta
              selección queda lista para cuando lo esté.
            </p>
            <Button disabled className="mt-3">
              Generar vista previa
            </Button>
          </CardContent>
        </Card>
      )}
    </main>
  );
}
