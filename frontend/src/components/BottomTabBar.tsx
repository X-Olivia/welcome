import type { ReactNode } from "react";

export type MobileTab = "map" | "activity" | "news";

interface BottomTabBarProps {
  activeTab: MobileTab;
  onChange: (tab: MobileTab) => void;
}

export function BottomTabBar({ activeTab, onChange }: BottomTabBarProps) {
  return (
    <nav className="bottom-tabbar mobile-glass" aria-label="Mobile navigation">
      <TabButton
        label="Map"
        tab="map"
        activeTab={activeTab}
        onChange={onChange}
        icon={<MapIcon />}
      />
      <TabButton
        label="Explore"
        tab="activity"
        activeTab={activeTab}
        onChange={onChange}
        icon={<CompassIcon />}
        emphasized
      />
      <TabButton
        label="News"
        tab="news"
        activeTab={activeTab}
        onChange={onChange}
        icon={<NewsIcon />}
      />
    </nav>
  );
}

interface TabButtonProps {
  label: string;
  tab: MobileTab;
  activeTab: MobileTab;
  onChange: (tab: MobileTab) => void;
  icon: ReactNode;
  emphasized?: boolean;
}

function TabButton({ label, tab, activeTab, onChange, icon, emphasized = false }: TabButtonProps) {
  const active = activeTab === tab;
  return (
    <button
      className={`bottom-tabbar__button ${active ? "bottom-tabbar__button--active" : ""} ${
        emphasized ? "bottom-tabbar__button--emphasized" : ""
      }`}
      type="button"
      onClick={() => onChange(tab)}
      aria-current={active ? "page" : undefined}
    >
      <span className="bottom-tabbar__icon" aria-hidden="true">
        {icon}
      </span>
      <span>{label}</span>
    </button>
  );
}

function MapIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9">
      <path d="m4 6.5 5-2 6 2 5-2v13l-5 2-6-2-5 2v-13Z" />
      <path d="M9 4.5v13M15 6.5v13" />
    </svg>
  );
}

function CompassIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9">
      <circle cx="12" cy="12" r="7.4" />
      <path d="m14.8 9.2-1.8 4.8-4.8 1.8 1.8-4.8 4.8-1.8Z" />
    </svg>
  );
}

function NewsIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9">
      <rect x="4" y="5" width="16" height="14" rx="2.8" />
      <path d="M8 9h2.5M8 13h8M8 16h5M13.5 9H16" strokeLinecap="round" />
    </svg>
  );
}
