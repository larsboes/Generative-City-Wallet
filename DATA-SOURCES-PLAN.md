# DATA SOURCES PLAN

## Remaining Planned Sources

- **Luma live API key path**
  - Adapter is implemented, but current environment still falls back until `LUMA_API_KEY` is set.

- **Live transit backend source (VVS/DB API)**
  - Still not integrated.
  - Transit currently uses OCR-driven input plus deterministic gating.

- **Native health APIs (Health Connect / Apple Health)**
  - Still not integrated.
  - Only abstraction fields and trust-policy handling are implemented.

- **Event fallback providers (Eventbrite/Meetup)**
  - Discussed in planning but not implemented.

- **Google Calendar local signal (`meeting_gap_min`)**
  - Planning-only; not implemented.
