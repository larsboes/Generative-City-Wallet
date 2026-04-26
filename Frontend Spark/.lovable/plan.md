## Goal

Embed a "press kit" style demo flow into the landing page (`/`) that simulates the full notification → app journey, triggered invisibly by 5 quick clicks anywhere on the page.

## Trigger

In `src/pages/Index.tsx`, add a top-level click listener on the page wrapper:
- Track click timestamps in a ref; if 5 clicks happen within 2.5s, set `demoOpen = true`.
- Counter resets on any pause >700ms between clicks so normal browsing never triggers it.
- Buttons/links continue to work normally — we don't `preventDefault`; the counter just observes.

## New component: `MockAndroidDemo`

Create `src/components/MockAndroidDemo.tsx` — a full-screen fixed overlay (`z-[100]`, covers viewport) styled as an Android 16 / One UI 8.1 lock screen.

### Visual design (One UI 8.1 lock screen)
- Background: a soft gradient wallpaper (deep blue → teal → warm grey) with subtle blur, mimicking Samsung's default One UI 8.1 wallpaper. Use CSS gradients only — no external images required.
- Status bar (top, ~28px): time on left in Samsung Sans-ish font (use `font-display`), right side shows signal/Wi-Fi/battery using lucide icons (`Signal`, `Wifi`, `BatteryFull`).
- Large lock-screen clock: huge time (e.g. `14:07`) in thin weight, date below (e.g. `Tue, 26 Apr · Munich`).
- Bottom: small "Swipe up to unlock" hint with a subtle chevron, and the One UI dual shortcut icons (phone left, camera right) as circular glass buttons.
- Notification stack centered vertically below clock, using One UI 8.1 notification card styling:
  - Rounded `rounded-3xl`, frosted glass `bg-white/15 backdrop-blur-2xl border border-white/20`, subtle shadow.
  - Header row: app icon (24px rounded square), app name in small caps, "now" / "5s ago" timestamp on right, small chevron.
  - Title (semibold) + body (regular) in white text.
  - Smooth slide-in-from-top + fade animation when each notification appears.

### Strava notification (appears immediately on demo start)
- App icon: small circle with the **Strava wordmark "S"** built in CSS — orange (`#FC4C02`) rounded square with a white stylised "S" (use an SVG path to recreate the Strava chevron-S logo so it's recognisable without bundling the trademark asset).
- App name: `Strava` · timestamp `now`
- Title: `Morning run complete 🎉`
- Body: `5.2 km · 27:14 · 5'14"/km — nice pace! Tap to view your activity.`

### Spark notification (appears 5s later, stacks above Strava)
- App icon: the existing Spark logo — primary-coloured rounded square with the `Sparkles` lucide icon (matches the brand mark used in the header of `Index.tsx`).
- App name: `Spark` · timestamp `now`
- Title: `Nice run! Cool down on us ❄️`
- Body: `We noticed you just finished a run nearby. Grab –10% on a cold drink at Landbäckerei IHLE — 5 min walk away.`
- Subtle pulse / haptic-style scale animation on appearance, plus a soft "ding" optional (skip audio to avoid autoplay issues).

### Auto-tap simulation (3s after Spark notification appears, ~8s into demo)
- Render an animated finger-tap ripple (expanding white circle + small dot) over the Spark notification card.
- The Spark card scales down briefly (`active:scale-95` style press), then the whole lock screen fades/zooms out while a fresh "app launching" splash zooms in:
  - Brief 600ms Spark splash (centered logo on `bg-background`) — mirrors the brand mark.
- Then `navigate("/wallet/offer/a3256d69-ed8b-4f93-855b-509d11dfd728")` to land on the real Landbäckerei IHLE Krapfen offer page.

### Controls
- Tiny `Skip demo` text button in the top-right corner of the overlay (only visible on hover / always faint) so testers can exit early — sets `demoOpen = false`.
- `Esc` key also closes the overlay.

## Wiring

1. Import `MockAndroidDemo` into `Index.tsx`. Render `{demoOpen && <MockAndroidDemo onExit={() => setDemoOpen(false)} />}` at the bottom of the page.
2. The component receives `onExit` and uses `useNavigate` from `react-router-dom` to perform the final navigation to the offer.
3. Auth caveat: `/wallet/*` is gated by `RequireAuth role="customer"`. If the demo viewer isn't signed in as a customer, they'll be redirected to `/auth`. To keep the demo seamless for press/judges, we'll:
   - Pass a query flag `?demo=1` on the navigation, and
   - In `RequireAuth`, when `?demo=1` is present and there's no session, allow render (or redirect to `/auth?redirect=/wallet/offer/...`). Simpler: just navigate; if unauth, the user lands on auth and can sign in. We'll keep the simple path and document this in code comments. (No DB change needed.)

## Files touched

- **edit** `src/pages/Index.tsx` — add 5-tap detector + render overlay.
- **new** `src/components/MockAndroidDemo.tsx` — the entire lock-screen + notification + auto-tap simulation.

No DB migrations, no edge functions, no new dependencies — uses existing Tailwind, lucide-react, and react-router.

## Acceptance

- Clicking 5 times rapidly anywhere on `/` opens a full-screen Android 16 / One UI 8.1 lock-screen mock.
- Strava notification slides in immediately with realistic copy and a Strava-style orange "S" mark.
- 5s later, Spark notification slides in above it.
- ~3s after that, an animated tap occurs on the Spark card; lock screen transitions to a brief Spark splash, then routes to the Landbäckerei IHLE Krapfen offer page in the wallet.
- `Esc` or the small "Skip" control exits the overlay cleanly.
- Normal navigation on the landing page is unaffected by the click counter.