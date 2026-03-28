interface TopBarProps {
  title?: string;
  logoSrc?: string;
}

export function TopBar({
  title = "CampusGuide",
  logoSrc = "/Nottingham_logo.png",
}: TopBarProps) {
  return (
    <div className="mobile-topbar mobile-glass">
      <div className="mobile-topbar__brand">
        <span className="mobile-topbar__icon" aria-hidden="true">
          <GlobeIcon />
        </span>
        <span className="mobile-topbar__title">{title}</span>
      </div>

      <div className="mobile-topbar__logo-shell">
        <img className="mobile-topbar__logo" src={logoSrc} alt="UNNC logo" />
      </div>
    </div>
  );
}

function GlobeIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9">
      <circle cx="12" cy="12" r="8.25" />
      <path d="M3.75 12h16.5" />
      <path d="M12 3.75c2.1 2.1 3.15 4.85 3.15 8.25S14.1 18.15 12 20.25c-2.1-2.1-3.15-4.85-3.15-8.25S9.9 5.85 12 3.75Z" />
    </svg>
  );
}
