"""통합 DB 스키마 정의 (정본). 설명은 docs/schema.md 참고.

사용 예::

    import pandas as pd
    from pacific_radio import schema

    df = schema.empty_frame()          # 빈 DB
    schema.validate(df)                # 컬럼·형식 검사, 문제 있으면 ValueError
"""
from __future__ import annotations

import pandas as pd

# 허용되는 핵종 표기. 새 핵종은 여기에 추가하고 docs/schema.md 도 갱신.
NUCLIDES: tuple[str, ...] = (
    "Cs-137",
    "Cs-134",
    "Sr-90",
    "Pu-238",
    "Pu-239",
    "Pu-240",
    "Pu-239+240",
    "Pu-241",
    # 비율 (활동도 농도가 아님). unit_orig 에 비율 종류를 적는다.
    "Pu-240/Pu-239",
    "Pu-238/Pu-239+240",
)

CTD_SOURCES: tuple[str, ...] = ("paired", "nearby", "woa", "none")
DATE_PRECISIONS: tuple[str, ...] = ("day", "month", "year", "unknown")
DEPTH_TYPES: tuple[str, ...] = ("measured", "nominal", "surface")
QC_FLAGS: tuple[str, ...] = ("ok", "suspect", "reject")

# 컬럼 이름 -> pandas dtype. 순서가 곧 DB 컬럼 순서.
COLUMNS: dict[str, str] = {
    # A. 추적
    "record_id": "string",
    "source_db": "string",
    "source_file": "string",
    "source_row": "Int64",
    "source_ref": "string",
    # B. 시료 위치·시간
    "cruise": "string",
    "station": "string",
    "sample_id": "string",
    "latitude": "float64",
    "longitude": "float64",
    "sampling_date": "datetime64[ns]",
    "date_precision": "string",
    "depth_m": "float64",
    "depth_type": "string",
    "region_orig": "string",
    # C. 핵종 측정값 (보고된 그대로)
    "nuclide": "string",
    "value_orig": "float64",
    "unit_orig": "string",
    "unc_orig": "float64",
    "unc_type_orig": "string",
    "below_dl": "boolean",
    "dl_value_orig": "float64",
    "ref_date_orig": "datetime64[ns]",
    "method_orig": "string",
    # D. 가공 값 (방침 결정 후 채움)
    "value_bq_m3": "float64",
    "unc_bq_m3": "float64",
    "decay_ref_date": "datetime64[ns]",
    "value_bq_m3_decay": "float64",
    "processing_version": "string",
    # E. CTD / 수괴
    "temperature_c": "float64",
    "salinity": "float64",
    "salinity_scale": "string",
    "ctd_source": "string",
    "ctd_note": "string",
    # F. 비고
    "qc_flag": "string",
    "notes": "string",
}

# 비어 있으면 안 되는 컬럼
REQUIRED: tuple[str, ...] = (
    "record_id",
    "source_db",
    "source_file",
    "source_row",
    "latitude",
    "longitude",
    "sampling_date",
    "depth_m",
    "nuclide",
    "value_orig",
    "unit_orig",
)


def empty_frame() -> pd.DataFrame:
    """스키마에 맞는 빈 DataFrame."""
    return pd.DataFrame({c: pd.Series(dtype=t) for c, t in COLUMNS.items()})


def make_record_id(source_db: str, source_file: str, source_row: int) -> str:
    return f"{source_db}:{source_file}:{int(source_row)}"


def validate(df: pd.DataFrame) -> None:
    """스키마 위반이 있으면 ValueError, 없으면 조용히 반환.

    검사 항목: 컬럼 집합, 필수값 결측, 핵종·범주 값, 위경도·수심 범위, record_id 중복.
    """
    problems: list[str] = []

    missing = [c for c in COLUMNS if c not in df.columns]
    extra = [c for c in df.columns if c not in COLUMNS]
    if missing:
        problems.append(f"빠진 컬럼: {missing}")
    if extra:
        problems.append(f"스키마에 없는 컬럼: {extra}")
    if problems:
        raise ValueError("; ".join(problems))

    for c in REQUIRED:
        n = int(df[c].isna().sum())
        if n:
            problems.append(f"필수 컬럼 '{c}' 결측 {n}행")

    def _check_categories(col: str, allowed: tuple[str, ...]) -> None:
        bad = df[col].dropna()
        bad = bad[~bad.isin(allowed)]
        if len(bad):
            problems.append(f"'{col}' 허용 외 값: {sorted(bad.unique().tolist())}")

    _check_categories("nuclide", NUCLIDES)
    _check_categories("ctd_source", CTD_SOURCES)
    _check_categories("date_precision", DATE_PRECISIONS)
    _check_categories("depth_type", DEPTH_TYPES)
    _check_categories("qc_flag", QC_FLAGS)

    lat = df["latitude"].dropna()
    if ((lat < -90) | (lat > 90)).any():
        problems.append("latitude 범위(-90~90) 벗어남")
    lon = df["longitude"].dropna()
    if ((lon < -180) | (lon > 360)).any():
        problems.append("longitude 범위(-180~360) 벗어남")
    depth = df["depth_m"].dropna()
    if (depth < 0).any():
        problems.append("depth_m 음수")

    dup = df["record_id"].dropna().duplicated()
    if dup.any():
        problems.append(f"record_id 중복 {int(dup.sum())}건")

    if problems:
        raise ValueError("; ".join(problems))
