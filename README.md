# Bedtime Sticker Club

A shared-tablet Home Assistant dashboard for three kids. Each child checks off
clearing their plate, brushing their teeth, and choosing tomorrow's outfit.
Completing all three earns a sticker on their monthly calendar.

![Tablet dashboard with independent progress and a chosen rocket sticker](docs/bedtime-tablet.png)

## Try it with Docker Compose

With Docker running, start the preview from this directory:

```sh
docker compose up -d --wait
```

Open [the preview dashboard](http://localhost:18123/bedtime-club/tonight).
On a fresh checkout, complete Home Assistant's onboarding to create your account,
then open **Bedtime Sticker Club** from the sidebar. This workspace's existing
`.test-ha/` account, settings, and sample progress are reused if present.

Compose starts Home Assistant 2026.10.1 and automatically downloads Button Card
7.0.1. The card is cached and verified on later starts; you do not need to install
HACS in this preview. Dashboard and package files are mounted directly from this
repository, while account information and saved stickers stay in the ignored
`.test-ha/` directory.

After editing `dashboards/bedtime.yaml`, refresh the dashboard. After editing
`packages/bedtime.yaml` or the preview configuration, run:

```sh
docker compose restart homeassistant
```

Useful commands:

```sh
docker compose logs -f homeassistant
docker compose down
```

Stopping the preview keeps its saved data. To start fresh without deleting your
previous preview, stop it and move the data directory aside before restarting:

```sh
docker compose down
mv .test-ha .test-ha-backup
docker compose up -d --wait
```

Choose a different backup name if `.test-ha-backup` already exists.

The preview defaults to localhost port **18123** and the **America/New_York**
timezone. To open it from a tablet on your local network:

```sh
BEDTIME_BIND_ADDRESS=0.0.0.0 docker compose up -d --wait
```

Then visit `http://YOUR_COMPUTER_LAN_IP:18123/bedtime-club/tonight` on the tablet.
`BEDTIME_PORT` and `BEDTIME_TIME_ZONE` can also override the defaults. Put these
variables in a local `.env` file if you want Compose to remember them.

## Install

Requires **Home Assistant 2026.10 or newer** and **Button Card 7.x**.
Validated with Home Assistant 2026.10.1 and Button Card 7.0.1.

1. Install [Button Card](https://github.com/custom-cards/button-card) through HACS.
   Confirm its JavaScript resource is registered as a module in **Settings →
   Dashboards → Resources** (enable Advanced Mode in your profile if needed).
   The usual resource URL is `/hacsfiles/button-card/button-card.js`.
2. Copy `packages/bedtime.yaml` into your Home Assistant `/config/packages/`
   directory and `dashboards/bedtime.yaml` into `/config/dashboards/`.
3. Merge the following into `/config/configuration.yaml`. If `homeassistant`,
   `packages`, `lovelace`, or `dashboards` already exists, extend that section;
   do not create a duplicate top-level key. If you already load packages from
   a directory, just put the package in that directory.

   ```yaml
   homeassistant:
     packages: !include_dir_named packages

   lovelace:
     dashboards:
       bedtime-club:
         mode: yaml
         title: Bedtime Sticker Club
         icon: mdi:star-face
         show_in_sidebar: true
         filename: dashboards/bedtime.yaml
   ```

   If your existing Lovelace setup manages resources in YAML (`mode: yaml`),
   add the resource to its existing `resources` list instead of using the UI:

   ```yaml
   resources:
     - url: /hacsfiles/button-card/button-card.js
       type: module
   ```

4. Run **Developer tools → YAML → Check configuration**, then restart Home
   Assistant. On the first startup, the package initializes empty checklists
   and the default reminder times. Later startups restore saved progress.
5. Open **Bedtime Sticker Club** from the sidebar, or visit
   `/bedtime-club/tonight`. Refresh the browser after installing Button Card.

## Make it yours

Near the bottom of `dashboards/bedtime.yaml`, each child has a short variables
block. Change `child_name`, `avatar`, `accent`, and `tint`. Keep `child_id` as
`kid_1`, `kid_2`, or `kid_3` so existing stickers stay associated with that child.
The two color values should be CSS colors; use a dark accent for readable text.

The gear at the top opens **Parent settings**, also available at
`/bedtime-club/parents`. Dinner defaults to **6 pm** and bedtime to **7 pm**.
Changing these helpers persists across restarts. Set dinner before bedtime,
with both times at or after 4 am. The parent page is a convenience, not an
access-control boundary.

The view uses Home Assistant's responsive Sections layout and a small, included
view theme. Three child cards fit across a 1024-pixel landscape tablet with the
sidebar collapsed; narrower screens use fewer columns. The theme only changes
spacing for this view. The sticker picker expands its child's card; short
screens may need vertical scrolling.

## How it behaves

- Before dinner: a preview of tonight's routine. At dinner: highlight clearing
  plates. At bedtime: highlight unfinished teeth and outfit tasks. Tasks always
  remain available.
- Finish all three: immediately earn ⭐ and choose from ⭐ 🌈 🚀 🦄 🦖 🐱 🦋 ⚽.
  Choosing again changes the emoji without adding another completed day.
- Undo a task: withdraw today's sticker and its credit. Complete the routine
  again to restore the chosen emoji and credit.
- The routine day changes at **4 am in Home Assistant's timezone**. Between
  midnight and 4 am, tasks and stickers still belong to the previous evening.
  At the start of a month, that also means the previous month's page remains
  visible until 4 am.
- Each child has the active month's dated stickers and a lifetime count.
  Previous months' detailed records are discarded at rollover. There are no
  rankings, penalties, reminders sent to devices, or sibling comparisons.
- A lost connection disables task and sticker actions. Changes appear after
  Home Assistant confirms them; offline taps are not queued for later.

## Storage and interfaces

The package uses nine date helpers, one initialized flag, two schedule helpers,
a routine sensor, and three restored trigger-based template sensors. Checkmarks
compare each task's saved date to the current routine date, so missing a 4 am
automation cannot leave yesterday's tasks checked. No external service or
custom backend integration is required.

Each child sensor (`sensor.bedtime_kid_1`, etc.) stores the lifetime count in its
state, plus `routine_date`, `month`, `tasks`, `completed`, and `stickers` attributes.
Sticker records map dates to `{emoji, earned}`; withdrawn stickers retain their
emoji for recompletion. The ledger ignores unavailable date helpers rather than
withdrawing their rewards.

The dashboard calls these scripts:

| Script | Required fields |
| --- | --- |
| `script.bedtime_set_task` | `child_id`, `task` (`plate`, `teeth`, `outfit`), `completed` (boolean), `routine_date` (`YYYY-MM-DD`) |
| `script.bedtime_choose_sticker` | `child_id`, `routine_date`, `sticker` (one of the eight supported emojis) |

Both use a shared queued dispatcher. Explicit completion values make duplicate
requests idempotent, and the submitted date prevents a stale screen from changing
a different routine day. Do not automate writes directly to the date helpers or
the internal sticker event; use these scripts.

Home Assistant restores the helpers and sensor attributes across normal
restarts. Include the Home Assistant storage directory in backups, keep entity
IDs stable, and leave `input_boolean.bedtime_initialized` on after installation.
Turning it off causes checklist dates and reminder times to initialize again on
the next startup. As with other HA helpers, an abrupt power loss can lose changes
made since the latest state save.

## Validation

The automated tests render the actual package's Jinja templates with Home
Assistant's template engine. Run them from this repository with Docker:

```sh
docker run --rm --entrypoint python \
  -v "$PWD:/work:ro" \
  ghcr.io/home-assistant/home-assistant:2026.10.1 \
  -m unittest discover -s /work/tests -v
```

They cover separate child progress, duplicate awards, emoji changes, undo and
recompletion, invalid sticker requests, midnight and 4 am, missed reset times,
month/year transitions, daylight-saving transitions, unavailable helpers,
first-start initialization, and reminder phases.

All 11 regression tests passed. The package also passed Home Assistant's
configuration checker and was exercised in an isolated Home Assistant container:
actual checklist taps, emoji selection, undo/recompletion, duplicate service
requests, stale/invalid requests, and persistence across a restart. Browser
checks covered tablet and phone layouts, the parent settings link, the offline
message and disabled actions, and reduced-motion behavior. The screenshot above
shows test progress with the bedtime highlight active.

After installing on your instance:

1. Complete a child's tasks. Check that ⭐ appears and the total increases once.
2. Pick 🚀, uncheck a task, then recheck it. The same sticker and count should return.
3. Check another child and confirm their progress stays separate.
4. Restart Home Assistant and verify the checkmarks, chosen sticker, total, and
   any changed reminder times persist.
5. Open the dashboard on your tablet and phone. Check readable labels, large
   buttons, the gear link, and the connection message during a brief disconnect.

If a card reports “Custom element doesn't exist: button-card,” check the HACS
resource and refresh the browser. If progress stays at “Waiting,” inspect
Settings → System → Logs and confirm the package's entities have the IDs above.
The package should be installed once; duplicate copies can create suffixed IDs.
