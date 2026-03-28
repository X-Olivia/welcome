interface NewsPageProps {
  query: string;
  onQueryChange: (value: string) => void;
}

type StoryItem = {
  category: string;
  title: string;
  blurb: string;
  detail: string;
};

const stories: StoryItem[] = [
  {
    category: "Student Spotlight",
    title: "Student A won some awards",
    blurb: "Recognized for outstanding contribution to campus sustainability projects.",
    detail:
      "Student A was honored for transforming campus waste management through a student-led recycling initiative and peer workshops.",
  },
  {
    category: "Academic Research",
    title: "Professors B published papers",
    blurb: "New findings in cognitive behavioural studies and educational technology.",
    detail:
      "Faculty members shared fresh interdisciplinary research results and highlighted how undergraduate students can engage in research culture.",
  },
  {
    category: "Campus Life",
    title: "Festival week returns",
    blurb: "Student societies are preparing events, performances, and open-campus moments.",
    detail:
      "Festival week will bring clubs, volunteering teams, and creative groups together across multiple campus venues.",
  },
];

export function NewsPage({ query, onQueryChange }: NewsPageProps) {
  const normalizedQuery = query.trim().toLowerCase();
  const filteredStories = stories.filter((story) => {
    if (!normalizedQuery) return true;
    return [story.category, story.title, story.blurb, story.detail]
      .join(" ")
      .toLowerCase()
      .includes(normalizedQuery);
  });

  return (
    <section className="tab-scene">
      <div className="news-page">
        <div className="news-page__search-row">
          <label className="news-page__search mobile-glass">
            <span className="news-page__search-icon" aria-hidden="true">
              <SearchIcon />
            </span>
            <input
              type="text"
              value={query}
              onChange={(event) => onQueryChange(event.target.value)}
              placeholder="Search campus stories"
            />
          </label>

          <button className="news-page__filter mobile-glass" type="button" aria-label="Filter stories">
            <FilterIcon />
          </button>
        </div>

        <div className="news-page__headline">
          <span className="news-page__headline-accent" />
          <h2>Latest Updates</h2>
        </div>

        <div className="news-list">
          {filteredStories.map((story, index) => (
            <article className="news-card" key={`${story.title}-${index}`}>
              <div className="news-card__media" aria-hidden="true">
                <StoryIcon variant={index} />
              </div>
              <div className="news-card__body">
                <span className="news-card__tag">{story.category}</span>
                <h3>{story.title}</h3>
                <p className="news-card__blurb">{story.blurb}</p>
                <p className="news-card__detail">{story.detail}</p>
                <button className="news-card__cta" type="button">
                  Read Full Story
                  <ArrowIcon />
                </button>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
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

function FilterIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9">
      <path d="M5 7h14M8 12h8M10.5 17h3" strokeLinecap="round" />
      <circle cx="7" cy="7" r="1.4" fill="currentColor" stroke="none" />
      <circle cx="16" cy="12" r="1.4" fill="currentColor" stroke="none" />
      <circle cx="13" cy="17" r="1.4" fill="currentColor" stroke="none" />
    </svg>
  );
}

function ArrowIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.1">
      <path d="M5 12h14M13 6l6 6-6 6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function StoryIcon({ variant }: { variant: number }) {
  if (variant % 3 === 0) {
    return (
      <svg viewBox="0 0 48 48" fill="none">
        <rect width="48" height="48" rx="12" fill="#183555" />
        <circle cx="24" cy="16" r="6" fill="#d6e6ff" />
        <path d="M14 34c2.8-5.5 6.6-8.2 10-8.2 3.4 0 7.2 2.7 10 8.2" fill="#416fb4" />
      </svg>
    );
  }
  if (variant % 3 === 1) {
    return (
      <svg viewBox="0 0 48 48" fill="none">
        <rect width="48" height="48" rx="12" fill="#0e223f" />
        <circle cx="24" cy="15" r="5" fill="#e7f2ff" opacity="0.92" />
        <path d="M14 31.5c4.8-8.6 15.2-8.6 20 0" stroke="#8fd1ff" strokeWidth="2.2" strokeLinecap="round" />
        <path d="M12 35c7-4.5 17-4.5 24 0" stroke="#365e96" strokeWidth="2.2" strokeLinecap="round" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 48 48" fill="none">
      <rect width="48" height="48" rx="12" fill="#1f3656" />
      <path d="M12 31c4.5-6.8 8.5-10.2 12-10.2S31.5 24.2 36 31" stroke="#b9dbff" strokeWidth="2.4" strokeLinecap="round" />
      <path d="M15 17h18M19 12h10" stroke="#567eb2" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  );
}
