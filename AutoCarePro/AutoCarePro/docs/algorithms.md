# The three algorithms

Everything below is implemented exactly as described — the constants live in
`js/constants.js` so they can be tuned without touching logic.

---

## 1. Maintenance due engine

**File:** `js/maintenance.js` → `statusFor()`, `scheduleFor()`, `fleetSummary()`

### Inputs

- The vehicle's current odometer.
- The **latest** record of each service type for that vehicle.
- The manufacturer interval for that type (`km` and `months`).

### Computation

```
dueOdometer = record.nextServiceOdometer ?? record.odometer + interval.km
dueDate     = record.nextServiceDate     ?? record.date     + interval.months

remainingKm   = dueOdometer - vehicle.odometer
remainingDays = dueDate     - today
```

An explicitly recorded "next service" always wins over the standard interval —
that is how a workshop's own advice is respected.

### Status

```
remainingKm < 0    OR remainingDays < 0    → OVERDUE
remainingKm <= 500 OR remainingDays <= 15  → DUE SOON
otherwise                                  → UPCOMING
no record for this type                    → NOT RECORDED
```

Both deadlines are evaluated and the *stricter* one decides. This is the whole
point: a weekend car hits the time limit first, a commuter car hits the distance
limit first, and one rule handles both.

### Interval consumption

```
kmConsumed  = (odometer - record.odometer) / interval.km
dayConsumed = daysSince(record.date) / (interval.months × 30.44)
consumed    = max(kmConsumed, dayConsumed)          // clamped to 0…2
```

`consumed` drives the progress bar on each service card and feeds the health
score. `1.0` means exactly due; `1.42` means 42% past due.

### Worked example (seeded demo, Hyundai i20)

```
Engine Oil — interval 5,000 km / 6 months
last record : 30,690 km, 150 days ago
dueOdometer : 30,690 + 5,000 = 35,690 km
odometer    : 35,240 km
remainingKm : 450        → ≤ 500  → DUE SOON
dueDate     : record + 6 months → 32 days away  → would be UPCOMING
result      : DUE SOON (distance deadline is stricter)
consumed    : max(4,550/5,000, 150/182.6) = 0.91
```

### Service interval table

| Service | km | months | Subsystem |
|---|---:|---:|---|
| Engine Oil | 5,000 | 6 | engine |
| Oil Filter | 5,000 | 6 | engine |
| Air Filter | 10,000 | 12 | engine |
| Fuel Filter | 20,000 | 24 | engine |
| Spark Plugs | 30,000 | 24 | engine |
| Coolant | 40,000 | 24 | engine |
| Brake Service | 15,000 | 12 | brakes |
| Brake Pads | 30,000 | 24 | brakes |
| Tyres | 40,000 | 36 | tyres |
| Wheel Alignment | 10,000 | 12 | tyres |
| Battery | 60,000 | 36 | battery |
| Chain Service | 5,000 | 6 | engine |
| General Service | 10,000 | 12 | engine |
| Repair / Other | — | — | — |

---

## 2. Vehicle Health Score

**File:** `js/health.js` → `calculateVehicleHealth(vehicle)`

### Returns

```js
{ overall, engine, tyres, battery, brakes, band, overdueCount, ageYears, factors }
```

All five scores clamped to **0–100**.

### Per-subsystem penalty

Each subsystem starts at 100 and loses three penalties:

**(a) Service wear** — take the *worst* `consumed` among the service types that
belong to that subsystem:

```
consumed ≤ 1 :  penalty = consumed² × 15            →  0 … 15
consumed > 1 :  penalty = 15 + (consumed − 1) × 50  →  capped at 60
no history   :  penalty = 25
```

The quadratic below 1.0 is deliberate. Being 50% through an oil interval costs
only 3.75 points, being 90% through costs 12.2, and being 40% *past* due costs
35 — which matches how mechanical risk actually behaves. A subsystem with no
recorded history is penalised 25 because unknown is not the same as healthy.

**(b) Age** — `min(10, yearsSinceModelYear × 0.8)`

**(c) Distance** — `min(10, odometer / 100,000 × 6)`

```
subsystemScore = clamp(100 − wear − age − distance, 0, 100)
```

### Overall

```
overall = engine×0.35 + brakes×0.25 + tyres×0.20 + battery×0.20
          − 4 × (number of currently OVERDUE services)
```

Engine is weighted highest because most service types map to it; brakes are
weighted above tyres and battery because a brake failure is a safety failure.
The overdue deduction exists because an overdue item is a *present* risk, not
gradual wear — it should visibly move the number.

### Bands

```
90–100  EXCELLENT
75–89   GOOD
50–74   ATTENTION REQUIRED
0–49    CRITICAL
```

### Worked example (seeded demo, Hyundai i20, 2022, 35,240 km)

```
age penalty      = 4 yr × 0.8         = 3.2
distance penalty = 35,240/100k × 6    = 2.1

engine  : worst = Engine Oil consumed 0.91 → 0.91² × 15 = 12.4
          100 − 12.4 − 3.2 − 2.1                        = 82
brakes  : worst = Brake Service consumed 0.82 → 10.1
          100 − 10.1 − 3.2 − 2.1                        = 85
tyres   : worst = Wheel Alignment consumed 0.58 → 5.0
          100 − 5.0 − 3.2 − 2.1                         = 90
battery : worst = Battery consumed 0.02 → 0.0
          100 − 0.0 − 3.2 − 2.1                         = 95

overall = 82×.35 + 85×.25 + 90×.20 + 95×.20 = 86.95 → 87
overdue = 0 → no deduction
band    = GOOD
```

And the contrast case (Honda City, 2021, 48,120 km, Oil Filter 1,620 km overdue,
no tyre or battery history):

```
engine  : Oil Filter consumed 1.42 → 15 + 0.42×50 = 36.2 → 57
brakes  : Brake Pads consumed 0.45 → 3.1          → 90
tyres   : no history → 25                          → 68
battery : no history → 25                          → 68
overall = 57×.35 + 90×.25 + 68×.20 + 68×.20 = 69.65 → 70 − 4 = 66
band    = ATTENTION REQUIRED
```

### Health trend

`healthTrend(vehicle, months)` replays the score month by month: it estimates
the odometer backwards from the vehicle's average daily distance and recomputes
the score using only the records that existed at that time. It is an
approximation used **only** for the trend chart; the headline number always
comes from live data.

---

## 3. Smart Wash Score

**File:** `js/washAdvisor.js` → `calculateWashScore(vehicle, environment)`

### Weights

| Factor | Max |
|---|---:|
| Time since wash | 60 |
| Pollution exposure | 20 |
| Road dust | 10 |
| Vehicle usage | 10 |
| **Total** | **100** |

### (1) Time — 60 points

```
weatherMultiplier = { Rain/Showers/Storm: 1.20, Snow: 1.25, Fog: 1.10, else 1.00 }
effectiveDays     = daysSinceWash × weatherMultiplier
timePoints        = clamp(effectiveDays / 20, 0, 1) × 60
```

20 days saturates the factor. Wet and foggy conditions deposit road spray and
grime faster, so elapsed time is weighted up rather than adding a separate term.

### (2) Pollution — 20 points

```
pollutionIndex = 0.50 × min(AQI  /300, 1)
               + 0.20 × min(PM2.5/150, 1)
               + 0.15 × min(PM10 /200, 1)
               + 0.08 × min(NO2  /100, 1)
               + 0.07 × min(O3   /120, 1)

pollutionPoints = pollutionIndex × 20
```

AQI dominates because it is the composite index; the individual pollutants
refine it. PM2.5 and PM10 outrank the gases because particulates are what
physically settle on paint.

### (3) Road dust — 10 points

```
coarse     = min(PM10 / 200, 1)
dryness    = clamp((70 − humidity) / 60, 0, 1)
journeyDust= distance-weighted dust level of trips since the last wash (0…1)
rainRelief = precipitation > 0.2 mm ? −0.25 : 0

dustIndex  = clamp(coarse×0.6 + dryness×0.2 + journeyDust×0.2 + rainRelief, 0, 1)
dustPoints = dustIndex × 10
```

### (4) Usage — 10 points

```
distanceRatio = clamp(distanceSinceWash / 500, 0, 1)
tripRatio     = clamp(tripsSinceWash / 6, 0, 1)
usagePoints   = distanceRatio × 7 + tripRatio × 3
```

`distanceSinceWash` is resolved in order of trustworthiness:

1. **odometer** — `odometer − odometerAtLastWash` (exact, when recorded);
2. **journeys** — sum of journeys logged since the wash date;
3. **estimated** — `daysSinceWash × estimatedDailyKm`, where the daily figure
   comes from recent journeys, else the odometer spread across service history,
   else the odometer spread across the vehicle's age.

The UI prints which source was used, so an estimate is never passed off as a
measurement.

### Score and bands

```
score = clamp(round(time + pollution + dust + usage), 0, 100)

 0–30  CLEAN      Vehicle condition is good. No wash required.
31–55  MONITOR    Monitor vehicle condition and environmental exposure.
56–75  WASH SOON  Vehicle wash is recommended soon.
76–100 WASH NOW   High contamination exposure detected. Wash recommended.
```

### Worked example (seeded demo, Hyundai i20)

```
12 days since wash, weather Clear (×1.00), 340 km driven, 3 trips
AQI 176 · PM2.5 78 · PM10 118 · NO2 40 · O3 56 · humidity 50%

time      = 12/20 × 60                                   = 36.0 / 60
pollution = (0.50×0.587 + 0.20×0.520 + 0.15×0.590
             + 0.08×0.400 + 0.07×0.467) × 20             = 11.0 / 20
dust      = (0.59×0.6 + 0.33×0.2 + 0.55×0.2) × 10        =  5.4 / 10
usage     = (340/500)×7 + (3/6)×3                        =  6.3 / 10
                                                          ─────────
score                                                     = 59 → WASH SOON
```

Record a wash and the score immediately drops to ~15 (**CLEAN**) because the
time factor resets to 0 and the odometer-at-wash is stamped.

### Why not "wash every 7 days"

Because the same seven days produce a score of 21 in clean, humid, low-use
conditions and 78 in AQI-300 air after 400 km of dusty highway. The score
distinguishes them; a calendar cannot.

---

## 4. Supporting calculations

**Environmental exposure** (`js/journeys.js` → `exposureSummary`) — distance-weighted
AQI, distance-weighted dust, and a blended exposure index
(`AQI 55% + dust 30% + total distance 15%`) banded LOW / MODERATE / HIGH.

**Alert engine** (`js/notifications.js`) — derives alerts from live state each
time a screen renders: overdue → CRITICAL, due-soon → WARNING, health < 50 →
CRITICAL, health < 75 → WARNING, wash ≥ 76 → WARNING, wash 56–75 → INFO,
AQI ≥ 201 → INFO/WARNING; sorted by priority; "ALL SYSTEMS NOMINAL" when the
list is empty. Nothing is stored — there is no hard-coded alert anywhere.

**Dashboard metrics** (`js/analytics.js` → `dashboardMetrics`) — vehicle count
from the collection length, service-due and overdue counts from `fleetSummary`,
maintenance cost from service records plus maintenance/repair expenses minus
expenses that were auto-created from those records (so nothing is double
counted).

**Cost per km** (`js/expenses.js` → `costPerKm`) — total spend divided by logged
journey distance when there is enough of it (>100 km), otherwise by the odometer.
