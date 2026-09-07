# Testing

## 1. Automated verification

The build was driven end-to-end in headless Chromium (Playwright) against a
local static server. **40 of 40 checks passed with zero application console
errors.** (The only network errors observed were the Google Fonts requests
blocked by the sandbox that ran the suite — the app falls back to system fonts,
which is the designed behaviour.)

### Boot & shell

| Check | Result |
|---|---|
| Splash screen removed after boot | PASS |
| Sidebar renders all 7 routes | PASS |
| Dashboard metric cards render | PASS |
| Primary vehicle hero renders (`Hyundai i20`) | PASS |
| Health score renders (`87`) | PASS |
| Dashboard chart canvas present | PASS |
| Unknown route falls back to dashboard | PASS |
| Service worker registers | PASS |

### Routing

| Route | Result |
|---|---|
| `#vehicles` · `#maintenance` · `#wash` · `#analytics` · `#expenses` · `#settings` | PASS (all 6) |

### Vehicle CRUD

| Check | Result |
|---|---|
| Add-vehicle modal opens | PASS |
| Empty form blocked with inline errors | PASS |
| Vehicle created (2 → 3 cards) | PASS |
| Success toast shown | PASS |
| Duplicate registration rejected (`pb11tt0001` vs `PB11 TT 0001`) | PASS |
| Set primary works | PASS |
| Delete asks for confirmation | PASS |
| Vehicle deleted (3 → 2 cards) | PASS |
| Primary reassigned after deleting the primary | PASS |

### Algorithm reactivity

| Check | Result |
|---|---|
| Health responds to a new service record (87 → 90) | PASS |
| Wash score drops after recording a wash (59 → 15) | PASS |
| Gauge stroke animates to the computed offset | PASS |
| Expense totals update on insert (₹190,806 → ₹192,306) | PASS |

### Data

| Check | Result |
|---|---|
| Data persists across a full reload | PASS |
| Export produces valid AutoCare Pro JSON | PASS |
| Import rejects a malformed file with a friendly error | PASS |

### Interaction

| Check | Result |
|---|---|
| Command palette opens with `Ctrl+K` | PASS |
| Palette navigates on `Enter` | PASS |
| All 8 analytics charts drawn | PASS |
| Bottom navigation visible at 390 px | PASS |
| Drawer opens at 390 px | PASS |

### Responsive — no horizontal overflow

| Width | Overflow | Result |
|---|---|---|
| 320 px | 0 px | PASS |
| 390 px | 0 px | PASS |
| 768 px | 0 px | PASS |
| 1024 px | 0 px | PASS |
| 1920 px | 0 px | PASS |

### Computed-state snapshot (seeded demo, verified in-browser)

```json
{
  "metrics": { "totalVehicles": 2, "serviceDue": 1, "overdue": 1,
               "maintenanceCost": 79420, "fleetHealth": 77 },
  "primary": "Hyundai i20",
  "health":  { "overall": 87, "engine": 82, "tyres": 90,
               "battery": 95, "brakes": 85, "band": "GOOD" },
  "next":    "Engine Oil · 450 km · due-soon",
  "wash":    { "score": 59, "status": "WASH SOON", "days": 12, "distance": 340,
               "factors": ["time 36/60", "pollution 11/20",
                           "dust 5.4/10", "usage 6.3/10"] },
  "honda":   { "health": 66, "band": "ATTENTION REQUIRED",
               "overdue": ["Oil Filter"] },
  "alerts":  ["critical: OIL FILTER OVERDUE",
              "warning: ENGINE OIL DUE SOON",
              "warning: VEHICLE HEALTH NEEDS ATTENTION",
              "warning: WASH RECOMMENDED",
              "info: WASH RECOMMENDED SOON"]
}
```

Note that `450 km` and `DUE SOON` were **derived**, not stored: the seed contains
only an engine-oil record at 30,690 km and an odometer of 35,240 km.

---

## 2. Manual checklist

Run through this before a demo or submission.

### Vehicles
- [ ] Add vehicle — required-field errors appear inline, then it saves
- [ ] Invalid year (1800 / 2100) rejected
- [ ] Negative odometer rejected
- [ ] Future last-service date rejected
- [ ] Last-service odometer greater than current odometer rejected
- [ ] Duplicate registration rejected regardless of case and spacing
- [ ] Edit loads existing values and saves changes
- [ ] Set primary moves the ribbon and updates the dashboard hero
- [ ] Delete asks for confirmation, then removes the vehicle and its records
- [ ] Deleting the primary promotes another vehicle
- [ ] Search, fuel filter and sort all narrow the list

### Maintenance
- [ ] Log a service — status, remaining distance and due date recalculate
- [ ] A record with an explicit next-service odometer overrides the interval
- [ ] Status filter and type filter work
- [ ] Edit and delete a record; a linked expense disappears with it
- [ ] Vehicle picker switches the schedule
- [ ] A type with no history shows NOT RECORDED with a call to action

### Expenses
- [ ] Record an expense — every summary tile and the chart update
- [ ] Vehicle / category / period filters work and reset pagination
- [ ] "Load 25 more" extends the ledger
- [ ] Edit and delete work

### Wash Advisor
- [ ] Gauge animates 0 → score and is coloured by band
- [ ] Factor points sum to the score
- [ ] Recording a wash resets time and usage; the score drops
- [ ] Logging a journey raises usage and advances the odometer
- [ ] Switching provider mode in Settings changes the reading and the score
- [ ] Denying location permission does not break anything

### Health
- [ ] Health rises after logging an overdue service
- [ ] A vehicle with no tyre/battery history shows lower subsystem scores
- [ ] Bands change colour at 90 / 75 / 50

### Data
- [ ] Refresh preserves everything
- [ ] Export downloads a dated JSON file
- [ ] Import restores it
- [ ] Import of a random JSON file shows a friendly error
- [ ] "Reset with demo data" restores the two demo vehicles
- [ ] "Erase everything" empties the app and shows empty states

### UI
- [ ] All seven routes render; browser back/forward work; refresh keeps the route
- [ ] No dead buttons anywhere
- [ ] Modals open, trap focus, close on Esc / backdrop / Cancel
- [ ] Toasts appear and auto-dismiss
- [ ] `Ctrl/⌘+K`, `1`–`7`, `N`, `?`, `Esc` all work
- [ ] Layout is correct at 320 / 375 / 390 / 430 / 768 / 1024 / 1280 / 1440 / 1920

### PWA
- [ ] Manifest valid in DevTools → Application
- [ ] Service worker activated; cache populated
- [ ] Install prompt available
- [ ] Offline reload still works

---

## 3. Reproducing the automated run

The suite is a standalone Playwright script (not shipped in the project folder,
since the deliverable has no build step). To recreate it:

```bash
npm init -y && npm i playwright
npx playwright install chromium
node test-app.js      # serves ./AutoCarePro and drives it headlessly
```

The script starts a static server, opens each route, exercises the CRUD flows,
reads computed values back out of the page with `page.evaluate(() => AC.…)`, and
asserts the responsive widths.
