# Apple Health Export & Telemetry Specification

## 1. Export Archive Structure

When exporting from the Apple Health iOS app (**Health app $\rightarrow$ Profile $\rightarrow$ Export All Health Data**), iOS packages an archive:

```
export.zip (or Health_data_from_Apple_Watch_.zip)
└── apple_health_export/
    ├── export.xml               # Primary XML payload (often 1GB - 5GB+)
    ├── export_cda.xml           # Clinical Document Architecture (HL7 CDA)
    ├── electroencephalogram/   # If EEG data exists
    └── workout-routes/          # GPX route files
        └── route_YYYY-MM-DD_*.gpx
```

## 2. Quantity & Category Type Mappings

| Apple Health Identifier | DB Table | Unit | Sampling Frequency | Clinical / Coaching Role |
|---|---|---|---|---|
| `HKQuantityTypeIdentifierRestingHeartRate` | `resting_hr` | count/min (bpm) | Daily scalar | Cardiovascular baseline, autonomic fatigue indicator |
| `HKQuantityTypeIdentifierHeartRateVariabilitySDNN` | `hrv_sdnn` | ms | Intermittent (~20-50/day) | Autonomic nervous system recovery & sympathetic tone |
| `HKQuantityTypeIdentifierVO2Max` | `vo2_max` | mL/min·kg | Post-outdoor workout | Aerobic engine capacity & longevity quartile |
| `HKCategoryTypeIdentifierSleepAnalysis` | `sleep_night` | Stage categories | Fragmented sessions | Physical and cognitive recovery architecture |
| `<Workout ...>` | `workouts` | Minutes, km, kcal | Discrete sessions | Training load, modality balance, periodization |

---

## 3. Sleep Stage Taxonomy & Aggregation Rules

Apple Health exports sleep as discrete categorical record fragments:

| Value | Category Meaning | Aggregation Rule |
|---|---|---|
| `HKCategoryValueSleepAnalysisInBed` | Time spent lying in bed | **EXCLUDE** from total sleep duration |
| `HKCategoryValueSleepAnalysisAwake` | Wakefulness after sleep onset (WASO) | **EXCLUDE** from total sleep duration |
| `HKCategoryValueSleepAnalysisAsleepCore` | Light / Core NREM sleep | **INCLUDE** in total sleep; store in `core_h` |
| `HKCategoryValueSleepAnalysisAsleepDeep` | Slow-Wave / Stage 3 NREM sleep | **INCLUDE** in total sleep; store in `deep_h` |
| `HKCategoryValueSleepAnalysisAsleepREM` | Rapid Eye Movement sleep | **INCLUDE** in total sleep; store in `rem_h` |
| `HKCategoryValueSleepAnalysisAsleepUnspecified` | Generic sleep (older watchOS / basic) | **INCLUDE** in total sleep |

### The 18:00 Night-Key Rule
Sleep sessions frequently span across midnight (e.g. 23:00 to 07:00). Grouping records by literal start calendar date splits single sleep sessions across two distinct calendar days.
To prevent this, the canonical night-key anchor offsets the start timestamp by 18 hours:
$$\text{night\_key} = (\text{start\_datetime} - 18\text{ hours}).\text{date()}$$
This correctly binds all sleep fragments starting between 18:00 on day $N$ and 17:59 on day $N+1$ to the night of day $N$.

---

## 4. Workout Structure & Nested Statistics

Workout entries contain workout metadata in attributes, and child `<WorkoutStatistics>` elements for physiological metrics:

```xml
<Workout workoutActivityType="HKWorkoutActivityTypeRunning"
         duration="45.0" durationUnit="min"
         startDate="2026-08-20 17:45:00 +0200"
         endDate="2026-08-20 18:30:00 +0200">
  <WorkoutStatistics type="HKQuantityTypeIdentifierActiveEnergyBurned" sum="420" unit="kcal"/>
  <WorkoutStatistics type="HKQuantityTypeIdentifierDistanceWalkingRunning" sum="6.5" unit="km"/>
  <WorkoutStatistics type="HKQuantityTypeIdentifierHeartRate" average="148" maximum="172" unit="count/min"/>
</Workout>
```

The parser strips the `HKWorkoutActivityType` prefix (yielding clean types such as `Running`, `Cycling`, `FunctionalStrengthTraining`, `TraditionalStrengthTraining`, `Walking`), normalizes duration to minutes, and extracts energy and heart rate parameters when available.
