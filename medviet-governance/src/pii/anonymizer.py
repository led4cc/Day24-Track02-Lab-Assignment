# src/pii/anonymizer.py
import pandas as pd
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
from faker import Faker
from .detector import build_vietnamese_analyzer, detect_pii

fake = Faker("vi_VN")


def _fake_cccd() -> str:
    return "".join(fake.random_choices(elements="0123456789", length=12))


def _fake_vn_phone() -> str:
    prefix = fake.random_element(elements=("03", "05", "07", "08", "09"))
    suffix = "".join(fake.random_choices(elements="0123456789", length=8))
    return f"{prefix}{suffix}"


def _fake_email(forbidden=None) -> str:
    forbidden = set() if forbidden is None else {str(value) for value in forbidden}
    replacement = fake.safe_email()
    while replacement in forbidden:
        replacement = fake.safe_email()
    return replacement


def _anonymize_cell(value, anonymize_func):
    if pd.isna(value):
        return value
    return anonymize_func(str(value))

class MedVietAnonymizer:

    def __init__(self):
        self.analyzer = build_vietnamese_analyzer()
        self.anonymizer = AnonymizerEngine()

    def anonymize_text(self, text: str, strategy: str = "replace") -> str:
        """
        Anonymize text với strategy được chọn.

        Strategies:
        - "mask"    : Nguyen Van A → N****** V** A
        - "replace" : thay bằng fake data (dùng Faker)
        - "hash"    : SHA-256 one-way hash
        - "generalize": chỉ dùng cho tuổi/năm sinh
        """
        results = detect_pii(text, self.analyzer)
        if not results:
            return text

        operators = {}

        if strategy == "replace":
            operators = {
                "PERSON": OperatorConfig("replace", 
                          {"new_value": fake.name()}),
                "EMAIL_ADDRESS": OperatorConfig("replace", 
                                 {"new_value": _fake_email()}),
                "VN_CCCD": OperatorConfig("replace", 
                           {"new_value": _fake_cccd()}),
                "VN_PHONE": OperatorConfig("replace", 
                            {"new_value": _fake_vn_phone()}),
            }
        elif strategy == "mask":
            operators = {
                "PERSON": OperatorConfig("mask", {
                    "masking_char": "*",
                    "chars_to_mask": 8,
                    "from_end": True,
                }),
                "EMAIL_ADDRESS": OperatorConfig("mask", {
                    "masking_char": "*",
                    "chars_to_mask": 8,
                    "from_end": False,
                }),
                "VN_CCCD": OperatorConfig("mask", {
                    "masking_char": "*",
                    "chars_to_mask": 8,
                    "from_end": True,
                }),
                "VN_PHONE": OperatorConfig("mask", {
                    "masking_char": "*",
                    "chars_to_mask": 6,
                    "from_end": True,
                }),
            }
        elif strategy == "hash":
            operators = {
                "PERSON": OperatorConfig("hash", {"hash_type": "sha256"}),
                "EMAIL_ADDRESS": OperatorConfig("hash", {"hash_type": "sha256"}),
                "VN_CCCD": OperatorConfig("hash", {"hash_type": "sha256"}),
                "VN_PHONE": OperatorConfig("hash", {"hash_type": "sha256"}),
            }
        elif strategy == "generalize":
            return text
        else:
            raise ValueError(f"Unsupported anonymization strategy: {strategy}")

        anonymized = self.anonymizer.anonymize(
            text=text,
            analyzer_results=results,
            operators=operators
        )
        return anonymized.text

    def anonymize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Anonymize toàn bộ DataFrame.
        - Cột text (ho_ten, dia_chi, email): dùng anonymize_text()
        - Cột cccd, so_dien_thoai: replace trực tiếp bằng fake data
        - Cột benh, ket_qua_xet_nghiem: GIỮ NGUYÊN (cần cho model training)
        - Cột patient_id: GIỮ NGUYÊN (pseudonym đã đủ an toàn)
        """
        df_anon = df.copy()

        if "ho_ten" in df_anon.columns:
            df_anon["ho_ten"] = df_anon["ho_ten"].apply(
                lambda value: _anonymize_cell(value, self.anonymize_text)
            )

        if "dia_chi" in df_anon.columns:
            df_anon["dia_chi"] = df_anon["dia_chi"].apply(
                lambda value: _anonymize_cell(value, self.anonymize_text)
            )

        if "email" in df_anon.columns:
            df_anon["email"] = [
                value if pd.isna(value) else f"anon_{index}@example.invalid"
                for index, value in enumerate(df_anon["email"])
            ]

        if "cccd" in df_anon.columns:
            df_anon["cccd"] = [_fake_cccd() for _ in range(len(df_anon))]

        if "so_dien_thoai" in df_anon.columns:
            df_anon["so_dien_thoai"] = [_fake_vn_phone() for _ in range(len(df_anon))]

        return df_anon

    def calculate_detection_rate(self, 
                                  original_df: pd.DataFrame,
                                  pii_columns: list) -> float:
        """
        Tính % PII được detect thành công.
        Mục tiêu: > 95%

        Logic: với mỗi ô trong pii_columns,
               kiểm tra xem detect_pii() có tìm thấy ít nhất 1 entity không.
        """
        total = 0
        detected = 0

        for col in pii_columns:
            for value in original_df[col].astype(str):
                total += 1
                results = detect_pii(value, self.analyzer)
                if len(results) > 0:
                    detected += 1

        return detected / total if total > 0 else 0.0
