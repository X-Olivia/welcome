import { FormEvent } from "react";

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  onVoiceClick?: () => void;
  placeholder?: string;
  isLoading?: boolean;
}

export function SearchBar({
  value,
  onChange,
  onSubmit,
  onVoiceClick,
  placeholder = "Where are you going?",
  isLoading = false,
}: SearchBarProps) {
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!value.trim() || isLoading) return;
    onSubmit();
  }

  return (
    <form className="mobile-searchbar mobile-glass" onSubmit={handleSubmit}>
      <button className="mobile-searchbar__icon-button" type="submit" aria-label="Search route">
        <SearchIcon />
      </button>

      <input
        className="mobile-searchbar__input"
        type="text"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        enterKeyHint="search"
        disabled={isLoading}
      />

      <button
        className="mobile-searchbar__icon-button mobile-searchbar__icon-button--voice"
        type="button"
        aria-label="Voice input"
        onClick={onVoiceClick}
      >
        {isLoading ? <SpinnerIcon /> : <MicIcon />}
      </button>
    </form>
  );
}

function SearchIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="11" cy="11" r="6.5" />
      <path d="m16 16 4.5 4.5" strokeLinecap="round" />
    </svg>
  );
}

function MicIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9">
      <rect x="9" y="4.2" width="6" height="10" rx="3" />
      <path d="M6.5 10.8a5.5 5.5 0 0 0 11 0" strokeLinecap="round" />
      <path d="M12 16.3v3.4" strokeLinecap="round" />
      <path d="M9.2 19.7h5.6" strokeLinecap="round" />
    </svg>
  );
}

function SpinnerIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M20 12a8 8 0 1 1-8-8" strokeLinecap="round" />
    </svg>
  );
}
