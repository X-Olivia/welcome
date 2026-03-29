# Product Brief — Hackathon Submission Template

> **Instructions**
> Complete all 6 required sections (A–F). Section G is optional but recommended.
> Be specific. Vague phrases like *"improves efficiency"* or *"leverages cutting-edge AI"* will score lower than concrete descriptions with real details.
> Quality over quantity.

---

## A · Problem Statement

> *Describe the problem your project addresses. A strong problem statement answers:
This welcoming robotic arm is a fun, playful, way that points to the directions，during open day.
> *— Who experiences this problem? (be specific)*
School reception volunteers, student guides, and front desk staff on open days; also new visitors (parents & prospective students) who often feel awkward or lack a warm interactive welcome when checking directions.
> *— In what situation does it occur?*
During school open days, campus visitor guides and reception staff face repetitive greeting and direction-pointing work throughout long event hours. 
> *— What happens when it is not solved — what is the cost or consequence?*
Staff easily suffer physical fatigue and burnout from repetitive movements; visitors receive rigid, formulaic greetings instead of a friendly, memorable campus first impression, reducing the overall warm and lively atmosphere of the open day.

**[Write your problem statement here]**
During open days, large crowds overwhelm limited volunteers. Complex campus layouts and poor digital guidance leave new visitors lost, while many hesitate to ask for help. Therefore, the playful robotic arm is designed to assist visitors with interactive greetings, directional guidance, and quick navigation access via QR codes.


---

## B · Solution

> *Describe what your product does. A strong solution description answers:*
> *— What are the 1–3 core features or capabilities?*
> *— How does a user actually interact with it? (describe the flow, not just the outcome)*
> *— How does each feature connect back to the problem described in Section A?*

Core Features
First, it is a playful robotic arm is designed to assist visitors with interactive greetings, directional guidance, and quick navigation access via QR codes. The robotic arm delivers expressive moving gestures to greet visitors and physically point toward destinations. Second, it supports simple voice interaction to understand visitors’ destination requests. Third, it displays a dynamic QR code that provides further navigation support.

User Interaction Flow
When visitors enter the campus entrance, the robotic arm automatically activates and greets them warmly. It then asks where they would like to go. After the visitor states their destination, the robotic arm moves smoothly and points toward the correct direction while displaying a QR code at the same time, for extra help.

Connection to the Problem
The arm’s playful motion and greeting design enrich the plain entrance atmosphere and add fun interaction for guests. Its pointing function offers an intuitive and vivid wayfinding experience. The QR code complements physical guidance by providing detailed digital navigation routes, making the visitor experience both engaging and comprehensive.

---

## C · Target Users

> *Define who this product is for. Avoid "everyone" or "any company."*
> *Include at least two of the following: role / industry / company size / behavior / pain trigger / usage frequency.*

**Primary user:**
 Prospective students and accompanying parents who visit the campus for open day events. They are first-time visitors unfamiliar with campus layouts, and they seek instant guidance upon entering the school on an annual/semester open day occasion.
 
**Usage scenario:**

> *Describe one concrete scenario in which your target user would open and use this product.*

The playful robotic arm is placed at the main campus entrance during university's open day. It actively greets incoming visitors, responds to their destination inquiries with gesture pointing, and displays navigation QR codes to offer convenient interactive guidance throughout their entry experience.

---

## D · Core Value Proposition

> *Complete the following sentence in 1–2 sentences. Then add a brief explanation.*
> *"For [target user], our product [does what], so that [outcome/benefit], unlike [current alternative]."*

**One-sentence value proposition:**
For general visitors on unviversity open days, our interactive robotic arm provides playful greetings, directional pointing and QR navigation guidance, so visitors can receive instant, approachable help without hesitation, unlike busy volunteers who are often overwhelmed and hard to approach.

**Brief explanation (2–4 sentences):**
The robotic arm creates a relaxed and fun welcoming atmosphere at the campus entrance. It offers simple interactive guidance anytime visitors arrive, removing the pressure of asking strangers for help. Compared with limited and overworked staff, the robot stays friendly and available non‑stop, making the open-day visiting experience smoother and more enjoyable for all guests.

---

## E · AI & Technical Approach

> *Describe the AI or technical components that power your product.*
> *Cover:*
> *— What type of AI / model / algorithm is used (e.g., LLM, vision model, classifier, embedding)?*
> *— What role does it play in the product? (what specific task does the AI perform?)*
> *— Why is this approach appropriate for the problem — why not a simpler rule-based solution?*

**AI / model type(s) used:**

- **Large Language Model (LLM)** — OpenAI GPT with structured output (JSON mode) for natural-language understanding.
- **A\* pathfinding algorithm** — graph-based shortest-path search on a pixel-level campus centerline network.
- **Haar cascade face detector (OpenCV)** — real-time frontal face detection for robotic-arm visual servoing.
- **Speech-to-Text / Text-to-Speech** — AssemblyAI (STT) and Cartesia (TTS) for voice interaction.

**Role of AI in the product:**

The LLM serves as the NLU core: it takes free-form visitor input (e.g., "I'm interested in AI and robotics") and produces a structured intent classification (`route` / `tour` / `recommend_tour` / `clarification`) together with normalized waypoint names. This structured output directly feeds the A\* route planner, which computes a real walkable path on the campus map. The face detector drives the SO-ARM101 robotic arm's multi-joint visual servo loop — when a visitor is detected, the arm tracks their face and can trigger a recorded greeting gesture. STT/TTS let visitors speak naturally instead of typing, and the system narrates route results aloud, making the interaction hands-free and accessible.

**Why AI is the right approach here:**

Visitor queries are open-ended and unpredictable — they range from specific destinations ("Where is the library?") to vague interests ("I like science stuff") to multi-stop requests ("Show me the engineering and arts buildings"). A rule-based keyword matcher would require exhaustive pattern lists and still fail on paraphrasing or mixed intent. The LLM handles linguistic diversity, intent ambiguity, and multi-turn clarification out of the box. Similarly, face tracking with a classical cascade detector is lightweight enough to run on-device at 20+ fps without a GPU, which suits the real-time servo loop on a Raspberry Pi–class host. A deep-learning face model would add latency and hardware cost without meaningful accuracy gains for the single-face, close-range scenario at a welcome desk.

---

## F · Key Assumptions

> *List 2–3 assumptions your solution depends on in order to work as intended.*
> *These are conditions you have not yet fully verified — be honest.*
> *Format: "We assume that [condition], because [reasoning]. This has / has not been validated by [evidence or note]."*

**Assumption 1:**

We assume that most visitors will interact with the system in Chinese (Mandarin) or simple English, because the open day audience at UNNC is predominantly mainland Chinese families with some international visitors. This has been partially validated by observing past open day demographics, but the NLU prompt and fallback logic have not yet been stress-tested with heavy dialect or code-switching input.

**Assumption 2:**

We assume that the campus centerline data extracted from the official map is accurate enough for pedestrian wayfinding — i.e., the pixel paths correspond to real walkable corridors and outdoor paths. This has been validated by manual spot-checking several routes against satellite imagery, but edge cases (construction zones, temporary closures on event day) have not been accounted for.

**Assumption 3 *(optional)*:**

We assume that a single SO-ARM101 robotic arm placed at the main entrance can physically point toward all eight compass directions without obstruction, and that visitors standing nearby can intuitively interpret the arm's gesture as a directional cue. This has not been validated in a live crowd setting — the arm's range of motion and gesture clarity may be less obvious when many people are gathered around the desk.

---

## G · Differentiation *(Optional — recommended)*

> *Briefly describe how your approach differs from existing solutions.*
> *You do not need formal competitive research — describe from your own experience or observation.*
> *Focus on a specific, concrete attribute (e.g., scope, speed, cost, modality, user type) rather than general claims like "better" or "smarter."*

**Current alternatives or common approaches:**

Most campus open days rely on printed maps, static signage, and human volunteers stationed at key intersections. Some schools offer a mobile app or WeChat mini-program with a pre-set map, but these require visitors to download/scan before they even know where to go. Volunteers are friendly but limited in number, get fatigued during long events, and can only help one person at a time.

**What makes our approach different:**

Our system combines three modalities that existing solutions treat separately: (1) **natural-language route planning** — visitors describe their intent in free text or voice and receive a real computed walking path, not a static list of landmarks; (2) **physical embodied guidance** — a robotic arm that greets, tracks faces, and physically points toward the route direction, giving visitors an immediate spatial cue without reading a map; (3) **seamless device handoff** — the route is not trapped on the kiosk screen; a QR code transfers the live route with full state to the visitor's phone so they can walk with it. No existing open-day solution we have observed integrates LLM-based intent understanding, real-time A\* pathfinding on an actual campus map, voice interaction, and a physically pointing robot into a single product loop.

---

