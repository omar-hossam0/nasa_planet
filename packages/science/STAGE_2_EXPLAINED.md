# Stage 2 explained: a beginner's guide to our data and outputs

**Audience:** you do not need experience in weather, climate or statistics.

**Project:** NASA Trend Detective - What the Average Hides.

**Current position:** Stage 2 prepares data for trend analysis. It has not yet
decided that a place is warming, drying or becoming greener. The QA/support
policy is still a candidate awaiting review before Stage 3.

## Read this first

Think of our data as a collection of maps, one for each month. Each map is
divided into small geographic boxes called **grid cells**. Each cell contains
a number, such as a monthly temperature or precipitation estimate.

Stage 2 asks:

> Which values can we use, which locations can we compare consistently, and
> how do we turn their numbers into meaningful monthly and yearly summaries?

The outputs include quality-filtered maps, a consistent set of usable cells,
regional averages, annual summaries, and departures from the seasonal reference.
They also record what was excluded and why.

You can read sections 1-8 for the concepts, sections 9-12 as a field dictionary,
and sections 13-17 to understand the figures, checks and next steps.

Quick navigation:

- [The four variables and their units](#1-the-four-things-we-measure)
- [What we did to the data](#5-what-stage-2-did-step-by-step)
- [What the actual coverage numbers mean](#8-what-our-actual-coverage-results-mean)
- [The prepared-data field dictionary](#9-prepared-netcdf-field-dictionary-the-main-data)
- [The JSON report field dictionary](#12-json-report-dictionary)
- [How to read the figures](#13-reading-the-four-figures)
- [Real worked examples](#14-read-a-real-example-from-our-output)

## 1. The four things we measure

| Plain name | Project ID | What the value represents | What it does not tell us by itself |
|---|---|---|---|
| Air temperature | `air_temperature` | Air temperature at about 2 metres above the ground, from the MERRA-2 reanalysis product | The temperature on a particular street or at a particular hour |
| Soil moisture | `soil_moisture` | Modeled water stored in the upper 0-10 cm of soil, from GLDAS | Humidity in the air, a percentage of wetness, or all water underground |
| Precipitation | `precipitation` | Estimated precipitation, from GPM IMERG; our prepared values express monthly water amounts | The exact timing or intensity of individual storms |
| Vegetation greenness | `vegetation_greenness` | The MODIS NDVI index, which describes a vegetation-greenness signal | Crop yield, percentage of land covered by plants, or a direct diagnosis of plant health |

**Reanalysis** combines observations with a physical model to reconstruct past
conditions. Soil moisture here is land-model output. The four products are not
four independent sets of weather-station observations.

### Units: how to read the numbers

| Unit in the files | Meaning | How to read it |
|---|---|---|
| `K` | Kelvin, a temperature scale | To display an absolute temperature in Celsius, subtract 273.15. Our stored temperatures stay in K. |
| `kg m-2` | Kilograms of water per square metre of ground | This describes water mass in the modeled soil layer. It is not a percentage. |
| `mm/hr` | Millimetres of water per hour | The source precipitation field is an average rate over its month, not an observation of every individual hour. |
| `mm` | Millimetres of accumulated water | Our prepared monthly rainfall amounts and annual rainfall totals use this unit. A regional value is an area-weighted average depth, not a total water volume. |
| `1` | Dimensionless: no physical unit | The number is not necessarily equal to one. NDVI, fractions, weights and flags can all be dimensionless, but they mean different things. |
| `sr` | Steradian, a solid-angle unit | Used only for the relative spherical size of a native cell. It is not a rainfall or temperature unit, and it is not square kilometres. |

An NDVI value of 0.12 **does not mean 12% vegetation coverage**. A coverage
fraction of 0.12, however, means 12% of its explicitly named denominator.
Always check the field name as well as the unit.

For temperature **differences**, a change of 1 K has the same numerical size
as a change of 1 degree Celsius. Do not subtract 273.15 from a temperature
anomaly; that subtraction is only for an absolute Kelvin temperature.

## 2. Where and when the data apply

We have monthly data from **January 2001 through December 2024**:

- 288 months in each regional cube.
- 24 calendar years.
- Four variables in each of three study rectangles: **12 variable-region pairs**.

| Readable name | Region ID | Bounding box: west, south, east, north |
|---|---|---|
| Nile study rectangle | `nile_corridor` | `[29, 24, 33, 32]` |
| Morocco study rectangle | `morocco_comparison` | `[-10, 30, -5, 35]` |
| Sahel study rectangle | `sahel_comparison` | `[-5, 12, 5, 17]` |

**Latitude** locates a point north or south. **Longitude** locates it east or
west. These coordinates are in degrees; negative longitudes here mean west.
A **bounding box**, or **bbox**, is simply the rectangle defined by those four
edges. An **AOI** is an area of interest selected for investigation.

These rectangles are not national borders or a map of farmland. For example,
the Nile rectangle includes much more than the river itself. Do not describe
its result as the average for all Egypt, or as a measurement of irrigated land.

The products have different grid sizes. Our Nile temperature cube has 17
latitude positions and 6 longitude positions; Nile NDVI has 160 and 80.
Those grids are kept separate. A temperature cell is not interchangeable with
an NDVI cell just because it has the same row/column number.

The original two Egypt cubes are also retained in the source folder. They are
parent/reference assets, not additional independent weather variables.

## 3. What does a data cube look like?

The `.nc` files are **NetCDF files**. They store several named arrays and their
descriptions together. They are not ordinary spreadsheets with a single table
of columns. Here, a field often needs both a date and a location to identify
one number.

| Coordinate/dimension | What it chooses | Example in this project |
|---|---|---|
| `time` | A monthly observation timestamp | A month in the 2001-2024 record; the original source timestamp is preserved |
| `lat` | A north/south cell-centre position | The latitude coordinate of a cell |
| `lon` | An east/west cell-centre position | The longitude coordinate of a cell |
| `year` | A calendar year for annual summaries | 2001, 2002, ... 2024 |

The Nile precipitation cube has shape **288 x 80 x 40**:
288 months, 80 latitude positions, and 40 longitude positions. That is 3,200
geographic cells, each with a monthly record.

In the dictionary below:

- **T** means monthly time.
- **Y** and **X** mean latitude and longitude positions.
- **A** means annual time, using the actual `year` coordinate.
- **T x Y x X** means a monthly map sequence.
- **T** alone means one value per month for the regional series.

If you exported a monthly map field to a spreadsheet, a row could identify
`time`, `lat`, `lon` and that field's value. If you exported a regional series,
a row would identify `time` and the regional value. The meaning of the value
depends on which field you chose.

## 4. The files to open, and what each is for

Paths in this table are relative to the repository root, `nasa_planet/`.

| File/folder | What is inside | Use it for |
|---|---|---|
| `data/nasa/measurements/` | The original combined source cubes | Source measurements and provenance; we do not overwrite these |
| `data/derived/science/phase_2/` | Twelve prepared cubes under the default strict policy, a manifest, and figures | The current prepared series and diagnostics |
| `data/derived/science/phase_2_standard/` | Three NDVI cubes under standard QA | An explicit alternative preparation comparison |
| `packages/science/config/preparation_policy.json` | The versioned rules for QA, geography, support and summaries | Exactly what choices the code applies |
| `packages/science/phase_reports/PHASE_2_COVERAGE.json` | Twelve human-readable summary records | Counts, coverage, units, source/output paths and hashes |
| `packages/science/phase_reports/PHASE_2_QA_SENSITIVITY.json` | Three standard-QA NDVI records | Compare the effect of relaxing the QA rules |
| `packages/science/phase_reports/PHASE_2_VALIDATION.json` | Results of reopening and checking the twelve default output files | File integrity and output consistency |
| `packages/science/notebooks/02_preprocessing.ipynb` | Executed calculations, printed summaries and four figures | The walkthrough of the actual preparation outputs |
| `packages/science/phase_reports/PHASE_2_REPORT.md` | The technical checkpoint report | Exact commands, acceptance checks and limitations |

The generated cube names follow this pattern:

```text
variable_id__region_id.nc

precipitation__nile_corridor.nc
vegetation_greenness__sahel_comparison.nc
```

The JSON reports summarize the cubes. They do not contain every monthly value
for every geographic cell. The prepared NetCDF files hold those arrays.

The derived folder is ignored by Git: it can be regenerated from the source
data and committed code. The notebook, policy and compact reports are kept in
the repository for review.

### Other audit files you may already have open

| File | How it relates to Stage 2 |
|---|---|
| `phase_reports/input_audit.json` in the statistics workspace | Historical first audit, before the explicit MODIS processed-field mapping. Its three recorded naming issues are historical findings, not the current field-contract status. |
| `phase_reports/input_audit_current.json` | The corrected source-input inventory: twelve matching field/unit contracts. It checks inputs, not QA policy suitability or trend significance. |
| `phase_reports/PHASE_1_INPUT_METADATA.json` | The first Nile precipitation exploration, including source units, conversion and provenance. It predates the Stage 2 fixed-support summaries. |

Read the current Stage 2 coverage, sensitivity and validation reports for the
prepared outputs. Keep the older audit records as history rather than assuming
every similarly named JSON file describes the same stage.

## 5. What Stage 2 did, step by step

### Step 1: open the validated source

The loader checks the product, variable name, units, monthly order and grid.
For MODIS, the original provider field name and our processed field name
`NDVI` are recorded separately. This prevents reading the wrong field.

### Step 2: select cells in the study area

We include cells whose **centres** lie inside the selected bbox, including
centres exactly on its edges. We reject invalid, empty, reversed, wrapping or
outside selections.

A cell is a box, even though its coordinate describes its centre. The code
uses the full selected cell for weighting; it does not cut that cell at the
drawn rectangle's edge. Consequently, the cell footprint can extend beyond
the requested bbox. Our area fractions describe the selected native cells,
not an exact calculation of the drawn polygon's area.

### Step 3: apply QA

**QA means quality assurance.** Here it means checking whether each sample
passes a stated preparation rule. A sample is one value in one cell in one
month.

- Temperature: retain finite values. This is a basic validity check, not a
  new independent scientific validation of the reanalysis.
- Soil moisture: retain finite, nonnegative values.
- Precipitation: retain finite, nonnegative values, and retain its quality
  index/error fields without inventing a quality threshold.
- NDVI: check its valid processed range and provider quality/reliability flags.

Rejected values become missing in the prepared analysis field. The original
source files remain unchanged. We do not invent replacement observations.

### Step 4: convert precipitation rates to amounts

The input is a **monthly average rate** in `mm/hr`. We multiply it by the
number of hours in that calendar month to obtain a monthly amount in `mm`.
February in a leap year and February in a non-leap year have different
durations; the code handles this.

This does not mean it rained at a constant rate every hour. It converts the
product's average rate into an amount for the whole month.

### Step 5: find a consistent group of cells

Our candidate rule keeps a cell in the analysis only if it passes QA in
**every month of the registered 2001-2024 reference period**. This group of
cells is called **fixed support**.

Why do this? If one monthly average uses coastal cells and another uses a
different set of desert cells, the averages may differ partly because we
changed which places we included. Fixed support holds the membership constant.

The tradeoff is exclusion: a cell can be removed from the final series
because of just one rejected month, even when its other months are usable.
This can leave a smaller or geographically unrepresentative subset.

The reference set stays fixed even if a later request selects a shorter
period. We do not silently select a more convenient new set of cells.

### Step 6: calculate area-aware regional means

We combine the retained cells into one number per month. Cells contribute
according to their relative spherical area, rather than simply their count.
The final contribution fractions are the normalized weights.

The implementation is tested with a **synthetic software example**, not NASA
weather observations: values 10 and 20 with area weights 2 and 1 produce
`(2 x 10 + 1 x 20) / 3 = 13.333...`. A simple equal-cell mean would give 15.
See `test_spherical_weights_match_hand_area_ratio` in the Stage 2 tests.

The real regional result represents **the retained cells**. It does not
automatically represent every location inside the study rectangle.

### Step 7: create annual summaries

| Variable | Annual operation | Meaning of one annual value |
|---|---|---|
| Precipitation | Add the twelve monthly amounts | Total precipitation depth for that calendar year, in mm; the regional value is an area-weighted mean depth |
| Temperature | Average monthly values with calendar-day weights | An annual mean in K, accounting for different month lengths |
| Soil moisture | Average monthly values with calendar-day weights | An annual mean modeled soil-water amount in kg m-2 |
| NDVI | Average monthly values with calendar-day weights | An annual mean of the monthly NDVI composites, still a unitless index |

All twelve months must be valid. A partial or missing year stays missing;
we do not fill a gap or scale a partial year up to a full year.

The annual axis is the actual calendar year. This helps prevent an annual
series from accidentally being treated as a series with monthly time steps.

### Step 8: calculate calendar-month anomalies

An **anomaly** means a difference from a reference value. It does not mean a
mistake or necessarily an extreme event.

For a January value, we subtract the average of January values over the
registered reference period. We compare July with the July reference, not
with January. This accounts for the recurring seasonal pattern in this
descriptive preparation.

- Positive anomaly: above the reference for that calendar month.
- Negative anomaly: below the reference for that calendar month.
- Zero anomaly: equal to that calendar-month reference, within numeric precision.

The anomaly keeps the physical unit: precipitation anomalies are mm,
temperature anomalies are K differences, and NDVI anomalies are unitless.
This project's reference is the delivered 2001-2024 period; it is not a claim
that this is a universally prescribed climate-normal period.

### Step 9: save evidence and check it again

We save the series, masks, weights, coverage and metadata. We then reopen the
files to check dimensions, dates, hashes, weights and selected calculations.
Passing those checks establishes consistency of this preparation, not the
physical truth of every source estimate or the significance of a climate trend.

## 6. Strict versus standard NDVI QA

MODIS supplies quality flags in addition to NDVI values. A decimal quality
number can encode several separate binary flags; it is not simply a score
where a larger number always means better or worse.

For the two low MODLAND quality bits:

| Code | Provider meaning in plain language |
|---|---|
| 0 | The index was produced with good quality |
| 1 | The index was produced, but other quality information needs checking |
| 2 | A cloudy/problematic observation |
| 3 | The index was not produced for other reasons |

The separate `pixel_reliability` field is easier to read:

| Code | Meaning |
|---|---|
| -1 | Fill/no processed data |
| 0 | Good data |
| 1 | Marginal data; needs other quality information |
| 2 | Snow/ice |
| 3 | Cloud |
| 4 | Estimated from the historical MODIS time series |

Our rules are:

| Mode | Accepted low quality bits | Accepted reliability codes | Tradeoff |
|---|---|---|---|
| `strict` | 0 | 0 | More restrictive; can exclude many otherwise useful cells over a long record |
| `standard` | 0 or 1 | 0 or 1 | Retains more data while admitting marginal observations |

Both modes also require a finite, valid-range NDVI value and valid flags.
Both exclude reliability 4 historical estimates rather than treating them
as new observations. Neither mode is a guarantee that every remaining value
is error-free. We did not choose a new threshold for IMERG's quality index.

These definitions were checked against the stored [MODIS V6.1 guide](../../data/nasa/expanded_v2/docs/MOD13_User_Guide_V61.pdf),
especially PDF pages 18 and 27-29. The CMG product's higher QA bits have a
different interpretation from some finer-resolution MODIS products; our code
does not accidentally use those high bits as the finer products' snow/shadow flags.

Strict is the current candidate default. The standard files are a comparison,
not an approved replacement chosen simply because their coverage is larger.

## 7. Zero, missing, excluded and insufficient data

| Item | Meaning | Example of the correct interpretation |
|---|---|---|
| Physical value `0` | A valid numeric amount, where the variable permits it | Zero precipitation is different from an unknown precipitation amount |
| `NaN` in a numeric array | No usable value in that field | Source missingness, QA rejection or exclusion from fixed support can produce it |
| `null` in JSON | Missing or not-applicable information, depending on its field | `qa.modis_mode: null` for a non-MODIS product means that mode is not applicable |
| `qa_accepted = 0` | That cell-month did not pass the selected validity/QA rule | It does not mean zero rainfall or zero vegetation |
| `fixed_support = 0` | That cell is excluded from the consistent analysis set | It may still have usable observations in other months |
| `insufficient_data` | Preparation could not create a usable fixed-support series | No cells pass the full-reference requirement |

Never replace all missing values with zero. Doing that would manufacture
dry months, colder conditions, less soil water or lower greenness.

In the current twelve default outputs, every pair has some retained cells,
so their preparation state is `prepared`. The code also tests the no-support
case and keeps its series missing rather than fabricating zeros.

## 8. What our actual coverage results mean

### Cells retained under strict/default preparation

| Variable | Region | Selected cells | Fixed-support cells | Excluded cells |
|---|---|---:|---:|---:|
| Temperature | Nile | 102 | 102 | 0 |
| Soil moisture | Nile | 512 | 459 | 53 |
| Precipitation | Nile | 3,200 | 3,200 | 0 |
| NDVI | Nile | 12,800 | 7,302 | 5,498 |
| Temperature | Morocco | 80 | 80 | 0 |
| Soil moisture | Morocco | 400 | 287 | 113 |
| Precipitation | Morocco | 2,500 | 2,500 | 0 |
| NDVI | Morocco | 10,000 | 3,019 | 6,981 |
| Temperature | Sahel | 160 | 160 | 0 |
| Soil moisture | Sahel | 800 | 800 | 0 |
| Precipitation | Sahel | 5,000 | 5,000 | 0 |
| NDVI | Sahel | 20,000 | 2,961 | 17,039 |

These are geographic cells, not numbers of months, people, stations or farms.

### NDVI retained area: the policy comparison

The denominator in this table is **the area of all selected full native cells
in that variable-region grid**. It is not a percentage of a country's total
area, exact polygon-intersection area, or certainty that a result is correct.

| Region | Strict retained area | Standard retained area |
|---|---:|---:|
| Nile | 57.50% | 90.29% |
| Morocco | 30.62% | 63.48% |
| Sahel | 14.69% | 82.59% |

Strict Sahel NDVI uses a much smaller subset. That subset may not represent
the entire rectangle. Standard keeps more area but accepts marginal data.
This is a review decision about quality and representation; coverage alone
does not establish which policy is scientifically best for the next analysis.

### Three different percentages: an actual Sahel example

All three statements below are true for strict Sahel NDVI, but answer different
questions:

1. About **94.62% of all selected cell-month samples** pass strict QA. A sample
   is one cell in one month; some cells fail in only a few months.
2. **2,961 / 20,000 = 14.805% of selected cells** pass in every reference month.
3. Those cells cover about **14.69% of selected native-cell area**, after area
   weighting. Cell sizes vary with latitude, so area share and cell share differ.

The 14.69% value does not mean the source is 14.69% accurate, that the other
85.31% has no vegetation, or that most individual observations are unusable.
The full-period rule is much stricter than passing QA in a particular month.

## 9. Prepared NetCDF field dictionary: the main data

In the next table, **physical unit** means `K` for temperature, `kg m-2` for
soil moisture, `mm` for prepared precipitation amounts, and `1` for NDVI.

| Field name | Dimensions | Unit | Meaning | What to use it for |
|---|---|---|---|---|
| `qa_monthly` | T x Y x X | Physical unit | Values after the selected product QA, before excluding cells from fixed support | Inspect which observations survive QA; do not substitute it for the fixed-support analysis field |
| `cell_monthly` | T x Y x X | Physical unit | Monthly values only in cells retained for the full-reference analysis set | The explicit per-cell monthly input for later slope work |
| `regional_monthly` | T | Physical unit | Area-weighted mean of retained cells for each month | The regional monthly chart and later regional slope input |
| `cell_monthly_anomaly` | T x Y x X | Same physical unit, as a difference | Each retained cell's departure from its own matching-calendar-month reference mean | Inspect cell-level seasonal departures |
| `regional_monthly_anomaly` | T | Same physical unit, as a difference | The regional series minus its matching-calendar-month reference mean | Inspect regional seasonal departures; it is not a trend estimate |
| `cell_annual` | A x Y x X | Physical unit | Complete-year total precipitation or day-weighted annual mean of the other variables | Per-cell annual analysis, using the actual year coordinate |
| `regional_annual` | A | Physical unit | Annual summary calculated from the fixed-support regional series | Regional annual chart and possible later annual slope input |

For precipitation, monthly and annual amounts both use mm, but their time
periods differ. Do not interpret an annual amount as a monthly amount merely
because their unit labels match. We sum across time for annual rainfall; we
do not add rainfall depths across cells to form the regional average.

For future analysis, explicitly select `cell_monthly` or `regional_monthly`,
or their appropriate annual forms. Do not select an arbitrary first field
from the file: diagnostic and ancillary arrays have different purposes.

## 10. Prepared NetCDF field dictionary: masks, coverage and weights

| Field name | Dimensions | Unit | Meaning | How to read it |
|---|---|---|---|---|
| `qa_accepted` | T x Y x X | `1` | Whether one cell-month passes the selected QA/validity rule | 1 = passes; 0 = rejected or missing |
| `fixed_support` | Y x X | `1` | Whether a cell passes in every reference month | 1 = retained in the analysis set; 0 = excluded |
| `qa_valid_fraction_by_cell` | Y x X | `1` | Fraction of reference months passing QA at each cell | 1 means all months; a smaller fraction means some months fail |
| `qa_valid_area_fraction_by_month` | T | `1` | Fraction of selected native-cell area with a QA-valid value in each month, before fixed-support exclusion | Inspect how monthly available area changes |
| `native_cell_solid_angle` | Y x X | `sr` | Relative spherical area of each selected full native cell | The area basis used to build weights, not an analysis result or square-kilometre area |
| `normalized_support_weight` | Y x X | `1` | A retained cell's fractional contribution to the regional mean | Retained-cell weights sum to 1; excluded cells have 0 weight when support is nonempty |

If no support exists, normalized weights and the regional series are missing.
They do not become a set of valid zero-valued weather measurements.

**Metadata correction:** while preparing this guide, we found that array
operations had copied weather units into some masks/fractions and `sr` into
normalized weights. Those labels are now corrected to dimensionless `1`, and
the genuine cell-area field remains `sr`. All numerical arrays in the twelve
default and three comparison files were checked against their previous
fingerprints and are unchanged. The output metadata revision is `1.1`; the
QA/support policy is still `prep-1.0.0` because its rules have not changed.

## 11. Product-specific source and quality fields

### Names in the original source versus prepared files

| Product/version | Original provider field recorded in the contract | Processed source-cube field | Main prepared analysis fields |
|---|---|---|---|
| MERRA-2 M2TMNXSLV 5.12.4 | `T2M` | `T2M` | `cell_monthly`, `regional_monthly` and annual/anomaly forms |
| GLDAS_NOAH025_M 2.1 | `SoilMoi0_10cm_inst` | `SoilMoi0_10cm_inst` | Same common prepared names, with soil-moisture units |
| GPM_3IMERGM 07 | `precipitation` | `precipitation` | Same common names; prepared amounts use mm |
| MOD13C2 061 | `CMG_0_05_Deg_Monthly_NDVI` | `NDVI` | Same common names; already scaled NDVI is not scaled again |

`T2M` and `SoilMoi0_10cm_inst` are product-specific names. The common prepared
names make downstream code consistent, while metadata preserves the original
identity. Do not mistake `source_variable`, `cube_variable` and `variable_id`
for three separate scientific quantities.

### Extra precipitation fields

| Field | Dimensions | Unit | What it means / why we retain it |
|---|---|---|---|
| `source_monthly_rate_after_qa` | T x Y x X | `mm/hr` | The QA-valid source rate, kept separately from the converted monthly mm amount; it is before fixed-support exclusion |
| `precipitationQualityIndex` | T x Y x X | `1` | The provider's quality index. It is retained without an invented numeric cutoff, probability interpretation or quality-based weight. |
| `randomError` | T x Y x X | `mm/hr` | The provider's random-error estimate for the source precipitation rate. It is not a p-value, a confidence interval for our trend, or an error value already converted into monthly mm. |

The ancillary precipitation fields stay in their source form. Stage 2 does
not propagate `randomError` into uncertainty for the regional mean, annual
total or a future trend.

### Extra NDVI fields

| Field | Dimensions | Unit | Purpose |
|---|---|---|---|
| `VI_Quality` | T x Y x X | `1` | Encoded provider QA flags; the selected low bits are used in our filter |
| `pixel_reliability` | T x Y x X | `1` | Provider summary categories, including good, marginal and historical-estimate codes |

These flags are retained for inspection. Do not average their numeric codes
and interpret that average as a weather quantity or an accuracy percentage.

## 12. JSON report dictionary

The coverage and sensitivity reports contain **metadata**: descriptions,
counts and file references. The dictionaries below explain the exact names
you will encounter. The main report has twelve `entries`; the comparison
report has three standard-MODIS `entries`.

### Top-level fields

| Key | Plain meaning |
|---|---|
| `policy_revision` | Internal name of the preparation-rule version, currently `prep-1.0.0`; not a NASA product version |
| `policy_sha256` | Fingerprint of the complete effective policy, including whether strict or standard was selected |
| `policy_review_status` | `candidate_pending_owner_review`: implemented and tested, but the preparation choice still needs review |
| `inference_status` | `not_computed`: we have not calculated trend significance or confidence here |
| `entries` | List of variable-region summaries |
| `documentation` | Source-document paths, URLs, page locators and checked file fingerprints |

A **hash** or **SHA-256 fingerprint** is a long identifier calculated from
file bytes or a policy's contents. It helps detect changes. It is not a
weather measurement, an accuracy score, or proof of scientific correctness.

### Identification and status inside each entry

| Key | Plain meaning |
|---|---|
| `output_metadata_revision` | Version of the output labels/schema; currently `1.1` after the diagnostic-unit correction |
| `preparation_state` | `prepared` means a usable fixed-support input series exists; `insufficient_data` means it does not. Neither is a significance verdict. |
| `variable_id` | One of our four scientific quantity IDs |
| `region_id` | One of our three study-rectangle IDs |
| `product_id` | Provider dataset identity, such as `GPM_3IMERGM` |
| `product_version` | Provider product version, such as `07`, `061`, `2.1` or `5.12.4` |
| `source_variable` | Original provider field name recorded in the input contract |
| `cube_variable` | Name of the field in the bundled processed source cube |
| `source_units` | Unit of that source-cube field, before our precipitation conversion |
| `policy_revision`, `policy_sha256`, `policy_review_status` | The effective rule version, fingerprint and review state used for this entry |
| `modis_mode` | The MODIS setting carried by the effective global policy. On a temperature/rainfall/soil entry this does not mean MODIS flags were applied to that product. |
| `inference_status` | Still `not_computed`; `prepared` does not override it |

### Dates, geography and selection

| Key | Plain meaning |
|---|---|
| `support_reference_start`, `support_reference_end` | Full registered period used to decide fixed support and the anomaly reference |
| `requested_start`, `requested_end` | Period requested for the output series; currently the full 2001-2024 range |
| `requested_bbox` | Requested `[west, south, east, north]` rectangle |
| `selection` | `native_cell_centres_inclusive_bbox`: select cells by their centres, including boundary centres |
| `weighting` | `full_native_spherical_cell_solid_angle`: use relative spherical areas of full native cells |
| `boundary_treatment` | Reminder that cells are not cut at the drawn bbox edge |
| `coverage_interpretation` | Reminder that the series represents retained QA-valid cells, not necessarily the entire rectangle |
| `selected_grid.lat_count`, `selected_grid.lon_count` | Numbers of selected latitude and longitude positions |
| `selected_grid.lat_centres`, `selected_grid.lon_centres` | First/last selected centre coordinates, not outer cell-edge boundaries |
| `analysis_months` | Number of monthly output timestamps; currently 288 |
| `annual_calendar_years` | Actual annual labels, 2001 through 2024 |
| `regional_valid_annual_count` | Number of annual regional values that are not missing; currently 24 in every default pair |

If a later request uses a shorter period, the fixed support and anomaly
baseline still use the full registered reference. QA counts describe that
reference over the selected bbox; they are not silently recalculated as if
only the shorter query period existed.

### Cell counts and coverage

| Key | Plain meaning / denominator |
|---|---|
| `selected_cell_count` | All selected geographic cells: latitude count x longitude count |
| `eligible_fixed_support_cells` | Cells passing QA in every registered reference month; eligible for preparation, not automatically for a future significance test |
| `excluded_from_fixed_support_cells` | Selected cells minus the fixed-support cells |
| `fixed_support_cell_fraction` | Fixed-support cell count divided by selected cell count |
| `fixed_support_area_fraction_of_selected_native_cells` | Area weight of the retained cells divided by area weight of all selected native cells |
| `qa_valid_area_fraction_reference_min` | Smallest monthly QA-valid area fraction anywhere in the reference period, before fixed-support exclusion |
| `qa_valid_area_fraction_reference_max` | Largest such monthly QA-valid area fraction |

These fractions are stored between 0 and 1. Multiply by 100 to display
percentages. They do not have rainfall or temperature units.

### Nested QA counts

| Key inside `qa` | Meaning |
|---|---|
| `source_finite_values` | Count of numeric, non-missing source cell-month samples before product QA |
| `accepted_values` | Count of cell-month samples passing the selected product QA/validity rules |
| `excluded_finite_values` | Previously finite samples rejected by QA; source values already missing are not counted again here |
| `total_values` | All selected reference cell-month slots, including missing ones: months x selected cells |
| `accepted_fraction_all_values` | Accepted cell-month samples divided by `total_values`; it is neither fixed-cell share nor retained-area share |
| `modis_mode` | `strict`/`standard` for a MODIS QA summary; `null` when not applicable to that product |
| `ancillary_threshold_applied` | `false` for GPM: we did not impose a quality-index cutoff; `null` when this particular information is not applicable |

For example, Nile NDVI has 12,800 selected cells and 288 months, giving
3,686,400 cell-month slots. This is why some QA counts are much larger than
the number of cells on a map.

### Units, files and warnings

| Key | Plain meaning |
|---|---|
| `monthly_units` | Unit of the prepared monthly analysis quantity |
| `annual_units` | Unit of the annual summary; read it together with the aggregation rule |
| `annual_aggregation` | Says whether the year is a sum of monthly amounts or a day-weighted mean |
| `warnings` | Important interpretation limits attached to this prepared result |
| `reason` | Explanation present for an insufficient-data result, for example no cells meeting the reference-support requirement |
| `source_cube_file` | Path to the original input cube |
| `source_cube_sha256` | Fingerprint of that source file |
| `artifact` | Path to the prepared output cube |
| `artifact_sha256` | Fingerprint of that exact generated output file; regenerating metadata changes this even when the data numbers stay the same |

The NetCDF file's **global attributes** repeat identification, policy, period,
selection and status information for that cube. They are descriptions, not
additional monthly columns of weather measurements.

### Documentation records

Each `documentation` record has `path`, `sha256`, `url`, `locator` and
`hash_verified`. These identify the locally stored guide, its fingerprint,
official source address, relevant page/table and whether its bytes match the
expected fingerprint. This check does not mean NASA approved our engine.

### Validation report

`PHASE_2_VALIDATION.json` contains:

| Key | Meaning |
|---|---|
| `purpose` | Explains that this is prepared-file verification, not trend-method validation |
| `policy_sha256` | Policy fingerprint being checked |
| `passed`, `total` | Number of default variable-region artifacts passing checks; currently 12 of 12 |
| `checks` | List of pair-level results |
| `checks[].variable_id`, `checks[].region_id` | Which pair was checked |
| `checks[].result` | `PASS` for a successful file check |
| `checks[].source_hash_unchanged` | Whether the source bytes match the earlier audited source |
| `checks[].round_trip_months`, `checks[].round_trip_years` | Monthly/annual counts after saving and reopening: 288 and 24 |

**Round trip** means saving a prepared file and opening it again to make sure
the stored result still has the expected content and labels.

## 13. Reading the four figures

### Coverage summary

![Coverage and fixed support](../../data/derived/science/phase_2/coverage_summary.png)

Each row is a variable-region pair. The horizontal axis is a fraction of
selected native-cell area. The blue bar is the smallest monthly QA-valid
area fraction over the reference. The orange bar is the area retained for
every month. These can differ greatly because passing QA once is easier
than passing in all 288 months.

### NDVI QA sensitivity

![Strict and standard NDVI preparation](../../data/derived/science/phase_2/qa_sensitivity.png)

This compares strict and standard retained fixed-support area. It tells us
how the preparation choice affects representation. Taller bars do not mean
greater statistical confidence or a stronger vegetation trend.

### Monthly and annual Nile series

![Nile monthly and annual prepared series](../../data/derived/science/phase_2/nile_prepared_series.png)

Each row is one variable. Left panels contain monthly regional means over
the retained cells. Right panels contain annual rainfall totals or annual
means for the other variables. Temperature is still in K. The NDVI unit
label `1` means unitless.

Spikes, seasonal cycles and year-to-year variation are visible. A line that
appears to rise on a plot is not, by itself, our tested conclusion about a
long-term trend. Stage 3 will calculate slopes; Stage 4 will address uncertainty.

### NDVI coverage and fixed-support maps

![Nile NDVI coverage and retained cells](../../data/derived/science/phase_2/nile_ndvi_support.png)

The left panel shows, cell by cell, the fraction of reference months passing
strict QA. The right panel shows the final fixed-support mask: 1 retained,
0 excluded. These are quality/selection maps, not maps of vegetation amount
and not significance maps.

These image links require the generated derived files. If they are absent
in a fresh checkout, regenerate them using the commands in the statistics
README or open the committed executed notebook, which includes the figures.

## 14. Read a real example from our output

The following are **calculated Stage 2 outputs**, rounded for readability.
They are not invented example observations, station reports or forecasts.

### One cell versus the region

In January 2001, the GPM cell at 28 N, 31 E has a monthly mean rate of about
**0.001 mm/hr**. January has 744 hours, so its prepared amount is about
**0.744 mm**. Small floating-point differences are retained in the stored file.

The area's `regional_monthly` value for that January is about **7.213 mm**.
That is different because it averages all retained cells with their area
weights. A single cell and a regional average answer different questions.

The regional precipitation total for calendar year 2001 is about **33.143 mm**.
This is the annual average depth over the selected retained cells, not the
rainfall at every location and not the total volume of water over Egypt.

### Interpreting an anomaly

For the same regional January 2001:

- Prepared amount: about **7.213 mm**.
- January reference mean across the registered period: about **9.035 mm**.
- Anomaly: about **-1.822 mm**.

Read this as: the regional January amount was below the January reference
mean for this prepared series. It does not establish a long-term drying trend
or explain its cause.

### Other variables in that same month

| Prepared Nile regional value, January 2001 | Plain interpretation |
|---|---|
| Temperature: about 286.236 K, or 13.086 degrees Celsius | Mean temperature over that product's retained cells for the month |
| Soil moisture: about 13.458 kg m-2 | Mean modeled water mass per ground area in the specified upper soil layer; not 13.458% moisture |
| NDVI: about 0.118709 | Mean greenness index over the strict retained NDVI cells; not 11.8709% vegetation coverage |

Each product has its own grid, QA and retained footprint. Putting these
numbers in the same table does not mean they measure identical pixels or
prove one variable caused another to change.

## 15. How to read the policy file

The [policy JSON](config/preparation_policy.json) is the recipe, rather than
the weather data. The most important settings are:

| Setting/group | Meaning |
|---|---|
| `status` | Still a candidate awaiting owner review |
| `spatial.selection` | How cells are selected by their centres |
| `spatial.weighting` | Full-cell spherical relative-area method |
| `spatial.boundary_intersection` | `false`: we do not cut edge cells to the exact bbox |
| `spatial.longitude_convention` | Supported longitude format; wrapping/antimeridian crossing is not implemented |
| `spatial.native_spacing_degrees` | Product grid spacing used and checked before calculating weights |
| `qa.modis_mode` | Current strict/standard choice for NDVI |
| `qa.modis_modes` | Exact accepted low-bit and reliability codes for both choices |
| `qa.modis_processed_ndvi_range` | Allowed already-scaled NDVI range, -0.2 through 1.0 |
| `qa.modis_quality_fill` | The encoded MODIS quality fill value that is rejected |
| `qa.imerg_quality_threshold` | `null`: no chosen numeric cutoff |
| `qa.imerg_quality_weighting` | `false`: the precipitation quality index does not set spatial weights |
| `qa.retain_ancillary_fields` | Keep quality/error information available for inspection |
| `qa.temperature`, `qa.soil_moisture`, `qa.precipitation` | Basic validity rules for the other products |
| `coverage.fixed_support` | Require a usable value in every registered reference month |
| `coverage.support_reference` | Use the full source period, not a silently changing query baseline |
| `coverage.minimum_support_cells` | One cell permits preparation; it does not establish regional representativeness or sufficient trend evidence |
| `coverage.minimum_area_fraction` | `null`: no separate minimum retained-area cutoff is imposed; the actual fraction is reported for review |
| `coverage.annual_required_months` | Require twelve valid months for an annual value |
| `coverage.imputation` | `none`: do not manufacture replacement values |
| `temporal` | Monthly precipitation conversion, annual aggregation, anomaly baseline and actual-year coordinate rules |
| `sources` | Official document addresses, local paths, hashes and page/table references |
| `limitations` | The representation, geometry and interpretation tradeoffs attached to these choices |

These are our proposed preparation choices, not NASA rules requiring every
project to use strict QA or complete-case support. They need review before
downstream scientific interpretation.

## 16. What has been checked, and what remains unknown

The combined suite now has **38 passing tests**: the earlier input tests,
Stage 2 preparation checks, and a new diagnostic-unit regression test added
while writing this guide. The twelve default files pass saved-file validation.

Checks cover field/unit identity, time gaps and duplicates, invalid selections,
QA categories, missing values, area weighting, consistent support, leap-year
rainfall conversion, incomplete annual records and calendar-month anomalies.
The metadata regression was observed failing before correction and passing
afterwards. Fingerprints confirm all numeric and coordinate arrays in the
15 regenerated default/comparison files are unchanged by the labeling fix.

Passing tests does not mean the NASA estimates are physically exact, that
our chosen retained subset represents the entire rectangle, or that a trend
is significant. The strict/standard policy decision remains pending.

Stage 2 has **not** produced:

- A trend slope or rate of long-term change.
- A p-value, confidence interval or significance verdict.
- A forecast of future weather.
- A cause of environmental change.
- A drought diagnosis or a combined drought score.
- Proof that an unchanging-looking regional average means every cell is stable.

The inherited annual-time-axis and spatial-minimum-length engine issues remain
separate later-stage work. The metadata correction described here does not
claim to fix those statistical issues.

## 17. Suggested reading order and next stage

1. Read this guide through section 8 to understand the concepts and coverage.
2. Open [02_preprocessing.ipynb](notebooks/02_preprocessing.ipynb) for the actual figures.
3. Open one `entries` record in [PHASE_2_COVERAGE.json](phase_reports/PHASE_2_COVERAGE.json), using section 12 as a dictionary.
4. Compare the three NDVI entries in [PHASE_2_QA_SENSITIVITY.json](phase_reports/PHASE_2_QA_SENSITIVITY.json).
5. Review the strict-versus-standard QA choice and whether the retained locations fit the intended question.
6. Consult [PHASE_2_REPORT.md](phase_reports/PHASE_2_REPORT.md) for the technical checks and commands.

After the checkpoint decision, **Stage 3** will estimate and test the behavior
of the trend slope estimator on known examples before trusting real slopes.
**Stage 4** will validate uncertainty and significance. Preparing a consistent
series is necessary for those stages, but does not replace them.

### Evidence behind this guide

The field definitions were checked against the actual generated NetCDF files,
the [preparation code](src/preparation.py),
[QA/temporal code](src/preprocessing.py),
[geographic/weighting code](src/regional_series.py),
[coverage report](phase_reports/PHASE_2_COVERAGE.json),
[QA comparison](phase_reports/PHASE_2_QA_SENSITIVITY.json), and
[validation record](phase_reports/PHASE_2_VALIDATION.json).
The [data README](../../data/nasa/README.md) and
[NASA product documentation manifest](../../data/nasa/expanded_v2/docs/guide_sources.json)
provide source context; the [IMERG ATBD](../../data/nasa/expanded_v2/docs/IMERG_V07_ATBD.pdf)
and MODIS guide referenced above describe the provider fields/quality flags.
All real examples above come from the local Stage 2 outputs. No trend result
or scientific approval is inferred from those descriptive values.
