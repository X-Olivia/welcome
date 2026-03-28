export type ActivityFilter = "scheduled" | "today" | "upcoming";

interface ActivityPageProps {
  filter: ActivityFilter;
  onFilterChange: (filter: ActivityFilter) => void;
  onConfirm: () => void;
  isSubmitting?: boolean;
}

type ActivityItem = {
  time: string;
  end: string;
  title: string;
  description: string;
  location: string;
  state: "add" | "done";
};

const activityContent: Record<ActivityFilter, ActivityItem[]> = {
  scheduled: [
    {
      time: "09:00",
      end: "10:00",
      title: "Opening Ceremony",
      description:
        "Welcome remarks by the University leadership and a compact overview of the day's highlights.",
      location: "Main Hall",
      state: "add",
    },
    {
      time: "10:30",
      end: "12:00",
      title: "Interactive Lab Sessions",
      description:
        "Hands-on demonstrations in robotics, biotech, and engineering project spaces across campus.",
      location: "Science Block C",
      state: "done",
    },
  ],
  today: [
    {
      time: "11:00",
      end: "12:00",
      title: "AI and Robotics Showcase",
      description:
        "Short demos, student projects, and open lab moments designed for quick discovery during the open day.",
      location: "Innovation Building",
      state: "add",
    },
    {
      time: "13:30",
      end: "14:20",
      title: "Campus Life Walkthrough",
      description:
        "A guided introduction to study spaces, food spots, and the rhythm of student life at UNNC.",
      location: "The Hub",
      state: "done",
    },
  ],
  upcoming: [
    {
      time: "15:00",
      end: "15:45",
      title: "Admissions Q&A",
      description:
        "A practical session covering applications, programmes, and the student journey from inquiry to arrival.",
      location: "Admissions Office",
      state: "add",
    },
    {
      time: "16:00",
      end: "17:00",
      title: "Innovation Stories",
      description:
        "A light campus session focused on entrepreneurship, maker culture, and future-facing projects.",
      location: "IEB",
      state: "add",
    },
  ],
};

const filterOptions: ActivityFilter[] = ["scheduled", "today", "upcoming"];

export function ActivityPage({
  filter,
  onFilterChange,
  onConfirm,
  isSubmitting = false,
}: ActivityPageProps) {
  const items = activityContent[filter];

  return (
    <section className="tab-scene">
      <div className="activity-page">
        <div className="activity-page__segmented mobile-glass">
          {filterOptions.map((option) => (
            <button
              key={option}
              className={`activity-page__segment ${filter === option ? "activity-page__segment--active" : ""}`}
              type="button"
              onClick={() => onFilterChange(option)}
            >
              {labelForFilter(option)}
            </button>
          ))}
        </div>

        <div className="activity-timeline">
          {items.map((item) => (
            <article className="activity-card" key={`${filter}-${item.time}-${item.title}`}>
              <div className="activity-card__time">
                <strong>{item.time}</strong>
                <span>{item.end}</span>
              </div>

              <div className="activity-card__line" aria-hidden="true">
                <span className="activity-card__dot" />
              </div>

              <div className="activity-card__body">
                <div className="activity-card__header">
                  <h3>{item.title}</h3>
                  <span
                    className={`activity-card__state ${
                      item.state === "done" ? "activity-card__state--done" : ""
                    }`}
                  >
                    {item.state === "done" ? <CheckIcon /> : <PlusIcon />}
                  </span>
                </div>
                <p>{item.description}</p>
                <span className="activity-card__location">
                  <PinIcon />
                  {item.location}
                </span>
              </div>
            </article>
          ))}
        </div>

        <button
          className="activity-page__cta"
          type="button"
          onClick={onConfirm}
          disabled={isSubmitting}
        >
          <span>{isSubmitting ? "Building Route..." : "Confirm and Generate Route"}</span>
          <ArrowIcon />
        </button>
      </div>
    </section>
  );
}

function labelForFilter(filter: ActivityFilter) {
  if (filter === "scheduled") return "Scheduled";
  if (filter === "today") return "Today";
  return "Upcoming";
}

function PinIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9">
      <path d="M12 20s6-5.5 6-10.1A6 6 0 1 0 6 9.9C6 14.5 12 20 12 20Z" />
      <circle cx="12" cy="10" r="2.1" />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
      <path d="M12 5v14M5 12h14" strokeLinecap="round" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
      <path d="m6.5 12.5 3.2 3.1 7.8-8.1" strokeLinecap="round" strokeLinejoin="round" />
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
