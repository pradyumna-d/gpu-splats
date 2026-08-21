import { Maximize2, RefreshCw, Rotate3D, RotateCcw, RotateCw, ZoomIn, ZoomOut } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { getOutputMetadata, sceneUrlFromMetadata, type SceneBounds } from "../services/api";

declare global {
  interface Window {
    requestAnimationFrame(callback: FrameRequestCallback): number;
  }
}

interface SplatViewerProps {
  jobId: string;
}

type Vector3 = [number, number, number];

interface CameraPose {
  position: Vector3;
  target: Vector3;
  up: Vector3;
}

const DEFAULT_BOUNDS: SceneBounds = {
  min: [-1, -1, -1],
  max: [1, 1, 1],
  center: [0, 0, 0],
  size: [2, 2, 2]
};

function cameraPoseForBounds(bounds: SceneBounds = DEFAULT_BOUNDS): CameraPose {
  const radius = Math.max(...bounds.size.map((size) => size / 2), 1);
  const distance = radius * 2.45;
  const [x, y, z] = bounds.center;
  return {
    position: [x, y - distance, z + radius * 0.45],
    target: bounds.center,
    up: [0, 0, 1]
  };
}

function applyCameraPose(viewer: any, pose: CameraPose) {
  viewer.camera?.position?.set?.(...pose.position);
  viewer.camera?.up?.set?.(...pose.up);
  viewer.camera?.up?.normalize?.();
  viewer.controls?.target?.set?.(...pose.target);
  viewer.camera?.lookAt?.(viewer.controls?.target ?? pose.target);
  viewer.controls?.update?.();
  viewer.forceRenderNextFrame?.();
  void viewer.runSplatSort?.(true, true);
}

function orbitCamera(viewer: any, radians: number) {
  const camera = viewer.camera;
  const target = viewer.controls?.target;
  if (!camera || !target) return;

  const dx = camera.position.x - target.x;
  const dy = camera.position.y - target.y;
  const cos = Math.cos(radians);
  const sin = Math.sin(radians);
  camera.position.set(target.x + dx * cos - dy * sin, target.y + dx * sin + dy * cos, camera.position.z);
  camera.lookAt(target);
  viewer.controls?.update?.();
  viewer.forceRenderNextFrame?.();
  void viewer.runSplatSort?.(true, true);
}

function dollyCamera(viewer: any, factor: number) {
  const camera = viewer.camera;
  const target = viewer.controls?.target;
  if (!camera || !target) return;

  camera.position.set(
    target.x + (camera.position.x - target.x) * factor,
    target.y + (camera.position.y - target.y) * factor,
    target.z + (camera.position.z - target.z) * factor,
  );
  camera.lookAt(target);
  viewer.controls?.update?.();
  viewer.forceRenderNextFrame?.();
  void viewer.runSplatSort?.(true, true);
}

export function SplatViewer({ jobId }: SplatViewerProps) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const viewerRef = useRef<any>(null);
  const cameraPoseRef = useRef<CameraPose>(cameraPoseForBounds());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [fps, setFps] = useState(0);
  const [autoOrbit, setAutoOrbit] = useState(
    () => new URLSearchParams(window.location.search).get("orbit") === "1",
  );

  useEffect(() => {
    let cancelled = false;
    let frameId = 0;
    let frames = 0;
    let last = performance.now();

    async function mountViewer() {
      if (!hostRef.current) return;
      setLoading(true);
      setError(null);
      try {
        const module = await import("@mkkellogg/gaussian-splats-3d");
        const splats = module as any;
        const metadata = await getOutputMetadata(jobId);
        const cameraPose = cameraPoseForBounds(metadata?.bounds);
        cameraPoseRef.current = cameraPose;
        if (cancelled) return;

        const viewer = new splats.Viewer({
          rootElement: hostRef.current,
          cameraUp: cameraPose.up,
          initialCameraPosition: cameraPose.position,
          initialCameraLookAt: cameraPose.target,
          sceneRevealMode: splats.SceneRevealMode?.Instant,
          sharedMemoryForWorkers: false,
          gpuAcceleratedSort: false,
          integerBasedSort: false,
          sphericalHarmonicsDegree: 2,
          maxScreenSpaceSplatSize: 96
        });
        viewerRef.current = viewer;
        await viewer.addSplatScene(sceneUrlFromMetadata(jobId, metadata ?? undefined), {
          splatAlphaRemovalThreshold: 1,
          progressiveLoad: false,
          showLoadingUI: false,
          position: [0, 0, 0],
          rotation: [0, 0, 0, 1],
          scale: [1, 1, 1]
        });
        applyCameraPose(viewer, cameraPose);
        viewer.start();
        setLoading(false);

        const tick = () => {
          frames += 1;
          const now = performance.now();
          if (now - last >= 1000) {
            setFps(frames);
            frames = 0;
            last = now;
          }
          frameId = window.requestAnimationFrame(tick);
        };
        tick();
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "Unable to load splat");
        setLoading(false);
      }
    }

    mountViewer();
    return () => {
      cancelled = true;
      cancelAnimationFrame(frameId);
      try {
        viewerRef.current?.dispose?.();
      } catch {
        viewerRef.current = null;
      }
    };
  }, [jobId]);

  useEffect(() => {
    if (!autoOrbit) return;

    let frameId = 0;
    let last = performance.now();
    const tick = (now: number) => {
      const seconds = Math.min((now - last) / 1000, 0.08);
      last = now;
      if (viewerRef.current) orbitCamera(viewerRef.current, seconds * 0.55);
      frameId = window.requestAnimationFrame(tick);
    };
    frameId = window.requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frameId);
  }, [autoOrbit]);

  const resetCamera = () => {
    if (viewerRef.current) applyCameraPose(viewerRef.current, cameraPoseRef.current);
  };

  const rotateLeft = () => orbitCamera(viewerRef.current, -Math.PI / 12);
  const rotateRight = () => orbitCamera(viewerRef.current, Math.PI / 12);
  const zoomIn = () => dollyCamera(viewerRef.current, 0.78);
  const zoomOut = () => dollyCamera(viewerRef.current, 1.28);

  const fullscreen = () => hostRef.current?.requestFullscreen?.();

  return (
    <div className="viewer-shell">
      <div ref={hostRef} className="viewer-canvas" />
      <div className="viewer-toolbar">
        <button className="icon-button" onClick={resetCamera} title="Reset camera">
          <RefreshCw size={17} />
        </button>
        <button className="icon-button" onClick={rotateLeft} title="Rotate left">
          <RotateCcw size={17} />
        </button>
        <button className="icon-button" onClick={rotateRight} title="Rotate right">
          <RotateCw size={17} />
        </button>
        <button className="icon-button" onClick={zoomIn} title="Zoom in">
          <ZoomIn size={17} />
        </button>
        <button className="icon-button" onClick={zoomOut} title="Zoom out">
          <ZoomOut size={17} />
        </button>
        <button
          className={`icon-button${autoOrbit ? " icon-button--active" : ""}`}
          onClick={() => setAutoOrbit((current) => !current)}
          title="Auto orbit"
          aria-pressed={autoOrbit}
        >
          <Rotate3D size={17} />
        </button>
        <button className="icon-button" onClick={fullscreen} title="Fullscreen">
          <Maximize2 size={17} />
        </button>
        <span className="fps">{fps} FPS</span>
      </div>
      {loading && <div className="viewer-overlay">Loading splat</div>}
      {error && <div className="viewer-overlay viewer-overlay--error">{error}</div>}
    </div>
  );
}
