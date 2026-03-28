interface PlaceCardProps {
  title: string;
  description: string;
  meta: string;
  tag: string;
  isOpen: boolean;
  onClose: () => void;
  onGo: () => void;
  onAddToRoute: () => void;
}

export function PlaceCard({
  title,
  description,
  meta,
  tag,
  isOpen,
  onClose,
  onGo,
  onAddToRoute,
}: PlaceCardProps) {
  return (
    <section className={`place-sheet ${isOpen ? "place-sheet--open" : ""}`}>
      <div className="place-sheet__handle" />
      <div className="place-sheet__header">
        <div className="place-sheet__title-wrap">
          <span className="place-sheet__pin" aria-hidden="true">
            <PinIcon />
          </span>
          <div>
            <p className="place-sheet__eyebrow">{tag}</p>
            <h3>{title}</h3>
          </div>
        </div>

        <button className="place-sheet__close" type="button" onClick={onClose} aria-label="Close place card">
          <CloseIcon />
        </button>
      </div>

      <p className="place-sheet__description">{description}</p>
      <p className="place-sheet__meta">{meta}</p>

      <div className="place-sheet__actions">
        <button className="place-sheet__secondary" type="button" onClick={onGo}>
          Go
        </button>
        <button className="place-sheet__primary" type="button" onClick={onAddToRoute}>
          Add to route
        </button>
      </div>
    </section>
  );
}

function PinIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9">
      <path d="M12 20s6-5.5 6-10.1A6 6 0 1 0 6 9.9C6 14.5 12 20 12 20Z" />
      <circle cx="12" cy="10" r="2.2" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
      <path d="m6 6 12 12M18 6 6 18" strokeLinecap="round" />
    </svg>
  );
}
