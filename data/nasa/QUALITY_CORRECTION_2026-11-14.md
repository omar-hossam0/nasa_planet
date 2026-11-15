# GLDAS Morocco source-fill correction

The downloaded GLDAS Morocco regional cube contained 32,544 values of `-9999` across 288 months (113 of 400 grid cells in every month). They are source fill values, not soil-moisture measurements. The first regional validation report counted them as finite and incorrectly reported full coverage.

The combined cube now stores these cells as missing (`NaN`). Its valid coverage is 287/400 cells, or 71.75%, in every month. The original monthly source subsets remain unchanged for provenance. `preprocess.apply_qa` also rejects negative GLDAS values to prevent a later source assembly from passing fill values into analysis.

Regenerated after the correction: `coverage_report.json`, `qa_policy.json`, `validation_regional_report.json`, all twelve evidence cards and spatial maps, the offline bundle, and the release acceptance report. The data revision changed. Previous analysis or receipt artifacts from the former revision must not be reused.

Validation: all 288 months remain present; finite values in this cube are nonnegative; nine scientific method checks and fifteen release checks passed. The checks establish pipeline consistency, not independent physical validation of the modeled soil moisture.
