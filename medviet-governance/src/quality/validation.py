# src/quality/validation.py
from pathlib import Path

import great_expectations as gx
import pandas as pd
from great_expectations.core.expectation_suite import ExpectationSuite
from great_expectations.expectations.expectation_configuration import (
    ExpectationConfiguration,
)

RAW_DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "raw" / "patients_raw.csv"
VALID_CONDITIONS = ["Tiểu đường", "Huyết áp cao", "Tim mạch", "Khỏe mạnh"]
EMAIL_REGEX = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
REQUIRED_COLUMNS = [
    "patient_id",
    "ho_ten",
    "cccd",
    "so_dien_thoai",
    "email",
    "benh",
    "ket_qua_xet_nghiem",
]


def _add_expectation(suite: ExpectationSuite, expectation_type: str, **kwargs) -> None:
    suite.add_expectation_configuration(
        ExpectationConfiguration(type=expectation_type, kwargs=kwargs)
    )


def build_patient_expectation_suite() -> ExpectationSuite:
    """Create the validation suite for anonymized patient data."""
    context = gx.get_context()
    suite = ExpectationSuite(name="patient_data_suite")

    _add_expectation(suite, "expect_column_values_to_not_be_null", column="patient_id")
    _add_expectation(
        suite,
        "expect_column_value_lengths_to_equal",
        column="cccd",
        value=12,
    )
    _add_expectation(
        suite,
        "expect_column_values_to_be_between",
        column="ket_qua_xet_nghiem",
        min_value=0,
        max_value=50,
    )
    _add_expectation(
        suite,
        "expect_column_values_to_be_in_set",
        column="benh",
        value_set=VALID_CONDITIONS,
    )
    _add_expectation(
        suite,
        "expect_column_values_to_match_regex",
        column="email",
        regex=EMAIL_REGEX,
    )
    _add_expectation(suite, "expect_column_values_to_be_unique", column="patient_id")

    context.suites.add_or_update(suite)
    return suite


def validate_anonymized_data(filepath: str) -> dict:
    """
    Validate anonymized data.
    Returns {"success": bool, "failed_checks": list, "stats": dict}.
    """
    df = pd.read_csv(filepath, dtype={"cccd": str, "so_dien_thoai": str})
    results = {
        "success": True,
        "failed_checks": [],
        "stats": {
            "total_rows": len(df),
            "columns": list(df.columns),
        },
    }

    def fail(check_name: str, detail: str) -> None:
        results["success"] = False
        results["failed_checks"].append({
            "check": check_name,
            "detail": detail,
        })

    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_columns:
        fail("required_columns", f"Missing columns: {missing_columns}")
        return results

    cccd_values = df["cccd"].astype(str)
    invalid_cccd = ~cccd_values.str.fullmatch(r"\d{12}")
    if invalid_cccd.any():
        fail("cccd_format", f"{int(invalid_cccd.sum())} values are not 12 digits")

    phone_values = df["so_dien_thoai"].astype(str)
    invalid_phone = ~phone_values.str.fullmatch(r"0[35789]\d{8}|[35789]\d{8}")
    if invalid_phone.any():
        fail(
            "phone_format",
            f"{int(invalid_phone.sum())} values are not valid VN phone numbers",
        )

    email_values = df["email"].astype(str)
    invalid_email = ~email_values.str.match(EMAIL_REGEX)
    if invalid_email.any():
        fail("email_format", f"{int(invalid_email.sum())} values are not valid emails")

    invalid_conditions = ~df["benh"].isin(VALID_CONDITIONS)
    if invalid_conditions.any():
        fail(
            "benh_values",
            f"{int(invalid_conditions.sum())} values are outside the allowed set",
        )

    out_of_range = ~df["ket_qua_xet_nghiem"].between(0, 50)
    if out_of_range.any():
        fail(
            "ket_qua_xet_nghiem_range",
            f"{int(out_of_range.sum())} values are outside [0, 50]",
        )

    null_counts = df[REQUIRED_COLUMNS].isna().sum()
    null_counts = null_counts[null_counts > 0].to_dict()
    if null_counts:
        fail("null_values", f"Null values found: {null_counts}")

    duplicate_patient_ids = int(df["patient_id"].duplicated().sum())
    if duplicate_patient_ids:
        fail("duplicate_patient_id", "Duplicate patient_id values found")

    if RAW_DATA_PATH.exists():
        original_df = pd.read_csv(RAW_DATA_PATH, dtype={"cccd": str, "so_dien_thoai": str})
        if len(df) != len(original_df):
            fail("row_count", f"Expected {len(original_df)} rows, found {len(df)}")

        output_text = df.astype(str).to_string(index=False)
        leaked_values = []
        for col in ["cccd", "so_dien_thoai", "email"]:
            if col not in original_df.columns:
                continue
            for value in original_df[col].dropna().astype(str).unique():
                if value and value in output_text:
                    leaked_values.append({"column": col, "value": value})
                    break
        if leaked_values:
            fail("original_pii_leak", f"Original PII values remain: {leaked_values}")

    results["stats"].update({
        "duplicate_patient_ids": duplicate_patient_ids,
        "null_counts": df[REQUIRED_COLUMNS].isna().sum().to_dict(),
    })

    return results
