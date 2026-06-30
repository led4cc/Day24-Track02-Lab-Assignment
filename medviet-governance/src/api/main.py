# src/api/main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse
import pandas as pd
from pathlib import Path
from src.access.rbac import get_current_user, require_permission
from src.pii.anonymizer import MedVietAnonymizer

app = FastAPI(title="MedViet Data API", version="1.0.0")
anonymizer = MedVietAnonymizer()
DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "raw" / "patients_raw.csv"


def load_patients() -> pd.DataFrame:
    if not DATA_PATH.exists():
        raise HTTPException(status_code=404, detail="Patient data not found")
    return pd.read_csv(DATA_PATH)

# --- ENDPOINT 1 ---
@app.get("/api/patients/raw")
@require_permission(resource="patient_data", action="read")
async def get_raw_patients(
    current_user: dict = Depends(get_current_user)
):
    """
    TODO: Trả về raw patient data (chỉ admin được phép).
    Load từ data/raw/patients_raw.csv
    Trả về 10 records đầu tiên dưới dạng JSON.
    """
    df = load_patients().head(10)
    return JSONResponse(content=df.to_dict(orient="records"))

# --- ENDPOINT 2 ---
@app.get("/api/patients/anonymized")
@require_permission(resource="training_data", action="read")
async def get_anonymized_patients(
    current_user: dict = Depends(get_current_user)
):
    """
    TODO: Trả về anonymized data (ml_engineer và admin được phép).
    Load raw data → anonymize → trả về JSON.
    """
    df = load_patients().head(10)
    df_anon = anonymizer.anonymize_dataframe(df)
    return JSONResponse(content=df_anon.to_dict(orient="records"))

# --- ENDPOINT 3 ---
@app.get("/api/metrics/aggregated")
@require_permission(resource="aggregated_metrics", action="read")
async def get_aggregated_metrics(
    current_user: dict = Depends(get_current_user)
):
    """
    TODO: Trả về aggregated metrics (data_analyst, ml_engineer, admin).
    Ví dụ: số bệnh nhân theo từng loại bệnh (không có PII).
    """
    df = load_patients()
    patients_by_condition = (
        df["benh"]
        .value_counts()
        .rename_axis("benh")
        .reset_index(name="so_benh_nhan")
        .to_dict(orient="records")
    )

    return JSONResponse(content={
        "total_patients": int(len(df)),
        "patients_by_condition": patients_by_condition,
        "average_test_result": float(df["ket_qua_xet_nghiem"].mean()),
    })

# --- ENDPOINT 4 ---
@app.delete("/api/patients/{patient_id}")
@require_permission(resource="patient_data", action="delete")
async def delete_patient(
    patient_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    TODO: Chỉ admin được xóa. Các role khác nhận 403.
    """
    df = load_patients()
    if patient_id not in set(df["patient_id"].astype(str)):
        raise HTTPException(status_code=404, detail="Patient not found")

    return {
        "status": "deleted",
        "patient_id": patient_id,
        "message": "Patient deletion authorized",
    }

@app.get("/health")
async def health():
    return {"status": "ok", "service": "MedViet Data API"}
