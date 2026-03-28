interface MapControlsProps {
  onZoomIn: () => void;
  onZoomOut: () => void;
  onLocate: () => void;
  canZoomIn?: boolean;
  canZoomOut?: boolean;
}

export function MapControls({
  onZoomIn,
  onZoomOut,
  onLocate,
  canZoomIn = true,
  canZoomOut = true,
}: MapControlsProps) {
  return (
    <div className="map-controls">
      <div className="map-controls__stack mobile-glass">
        <button
          className="map-controls__button"
          type="button"
          onClick={onZoomIn}
          disabled={!canZoomIn}
          aria-label="Zoom in"
        >
          <PlusIcon />
        </button>
        <button
          className="map-controls__button"
          type="button"
          onClick={onZoomOut}
          disabled={!canZoomOut}
          aria-label="Zoom out"
        >
          <MinusIcon />
        </button>
      </div>

      <button
        className="map-controls__locate mobile-glass"
        type="button"
        onClick={onLocate}
        aria-label="Center on location"
      >
        <LocateIcon />
      </button>
    </div>
  );
}

function PlusIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
      <path d="M12 5v14M5 12h14" strokeLinecap="round" />
    </svg>
  );
}

function MinusIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
      <path d="M5 12h14" strokeLinecap="round" />
    </svg>
  );
}

function LocateIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9">
      <circle cx="12" cy="12" r="6" />
      <path d="M12 2.9v3.2M12 17.9v3.2M21.1 12h-3.2M6.1 12H2.9" strokeLinecap="round" />
      <circle cx="12" cy="12" r="2.2" fill="currentColor" stroke="none" />
    </svg>
  );
}
