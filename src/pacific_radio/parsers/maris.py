"""IAEA MARIS NetCDF (해수 그룹) → 통합 스키마 파서.

MARIS 파일 형식 (IAEA `marisco` 패키지 템플릿에서 확인, docs/data_sources.md A1)
------------------------------------------------------------------------------
- 그룹: seawater / biota / sediment / suspended_matter. 이 파서는 seawater 만 읽는다.
- 한 행 = 한 측정값 (long format). 차원 이름 'id'.
- 변수: id, id_provider, lon, lat, smp_depth, tot_depth, time, area, station, smp_id,
        nuclide, value, unit, unc, dl, dlv, filt, count_met, samp_met, prep_met, lab,
        vol, sal, temp, ph  (파일마다 일부만 존재)
- time: 1970-01-01 기준 초 (UTC), uint64.
- nuclide/unit/dl/area/filt/… 는 NetCDF enum 타입. 파일 안에 {이름: 코드} 사전이 들어 있어
  그것으로 해석하고, enum 이 아니면 data/external/maris_lut/*.csv 로 해석한다.
- value/unc/dlv 는 float32. unit 의 기본은 'Bq per m3' (코드 1).

사용 예
-------
    from pacific_radio.parsers import maris
    df, report = maris.parse("data/raw/maris/123.nc")          # 태평양 해수만
    df, report = maris.parse("data/raw/maris/123.nc", pacific_only=False)

명령줄
------
    python -m pacific_radio.parsers.maris data/raw/maris/*.nc --out data/processed/maris_pacific_seawater
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import netCDF4 as nc
import numpy as np
import pandas as pd

from .. import schema
from ..regions import pacific_mask
from ..store import write_processed

SOURCE_DB = "maris"

# MARIS nc_name → 통합 스키마 핵종명. 여기 없는 핵종은 버리고 report 에 센다.
NUCLIDE_MAP: dict[str, str] = {
    "cs137": "Cs-137",
    "cs134": "Cs-134",
    "sr90": "Sr-90",
    "pu238": "Pu-238",
    "pu239": "Pu-239",
    "pu240": "Pu-240",
    "pu241": "Pu-241",
    "pu239_240_tot": "Pu-239+240",
    "pu240_pu239_ratio": "Pu-240/Pu-239",
    "pu238_pu239_240_tot_ratio": "Pu-238/Pu-239+240",
}

# enum 이름(unit_sanitized) → 단위 문자열. dbo_unit.csv 와 같다. 파일 enum 이 없을 때의 보조.
UNIT_NAME_MAP: dict[str, str] = {
    "Bq per m3": "Bq/m3", "Bq per m2": "Bq/m2", "Bq per kg": "Bq/kg", "Bq per kgd": "Bq/kgd",
    "Bq per kgw": "Bq/kgw", "kg per kg": "kg/kg", "TU": "TU", "DELTA per mill": "DELTA/mill",
    "atom per kg": "atom/kg", "atom per kgd": "atom/kgd", "atom per kgw": "atom/kgw",
    "atom per l": "atom/l", "Bq per kgC": "Bq/kgC",
    "NOT AVAILABLE": "NOT AVAILABLE", "Not applicable": "Not applicable",
}
BELOW_DL_NAMES = frozenset({"Detection limit", "Not detected"})
NA_NAMES = frozenset({"NOT AVAILABLE", "Not available", "NOT APPLICABLE", "Not applicable"})

# enum 변수명 → 조회표 CSV (파일에 enum 이 없을 때)
LUT_FILES = {
    "nuclide": ("dbo_nuclide.csv", "nuclide_id", "nc_name"),
    "unit": ("dbo_unit.csv", "unit_id", "unit_sanitized"),
    "dl": ("dbo_detectlimit.csv", "id", "name_sanitized"),
    "area": ("dbo_area.csv", "areaId", "displayName"),
    "filt": ("dbo_filtered.csv", "id", "name"),
    "count_met": ("dbo_counmet.csv", "counmet_id", "counmet"),
    "samp_met": ("dbo_sampmet.csv", "sampmet_id", "sampmet"),
}


def default_lut_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "external" / "maris_lut"


# --------------------------------------------------------------------------- 읽기
def _decode_var(var: nc.Variable, name: str, lut_dir: Path) -> np.ndarray:
    """enum/코드 변수를 이름 문자열 배열로. 비 enum 변수는 값 그대로."""
    raw = var[:]
    if isinstance(var.datatype, nc.EnumType):
        code_to_name = {v: k for k, v in var.datatype.enum_dict.items()}
        codes = np.ma.filled(raw, -1).astype(np.int64)
        return np.array([code_to_name.get(int(c), f"UNKNOWN_CODE_{int(c)}") for c in codes], dtype=object)
    if name in LUT_FILES and np.issubdtype(np.asarray(raw).dtype, np.integer):
        fname, key, val = LUT_FILES[name]
        lut = pd.read_csv(lut_dir / fname)
        code_to_name = dict(zip(lut[key].astype(int), lut[val].astype(str)))
        codes = np.ma.filled(raw, -1).astype(np.int64)
        return np.array([code_to_name.get(int(c), f"UNKNOWN_CODE_{int(c)}") for c in codes], dtype=object)
    if np.issubdtype(np.asarray(raw).dtype, np.floating):
        return np.ma.filled(raw, np.nan).astype(float)
    if isinstance(raw, np.ma.MaskedArray):
        return raw.filled("" if raw.dtype.kind in "OUS" else 0)
    return np.asarray(raw)


def read_seawater(path: str | Path, lut_dir: Path | None = None) -> tuple[pd.DataFrame, dict]:
    """MARIS NetCDF 의 seawater 그룹을 '해석된' 원시 표로 읽는다 (스키마 변환 전).

    반환: (DataFrame[열 = MARIS 변수명, 코드는 이름으로 해석됨], 전역 속성 dict)
    """
    path = Path(path)
    lut_dir = lut_dir or default_lut_dir()
    with nc.Dataset(path, "r") as ds:
        attrs = {k: ds.getncattr(k) for k in ds.ncattrs()}
        if "seawater" not in ds.groups:
            return pd.DataFrame(), attrs
        g = ds.groups["seawater"]
        data = {}
        for vn, var in g.variables.items():
            if vn in g.dimensions:
                continue
            data[vn] = _decode_var(var, vn, lut_dir)
        raw = pd.DataFrame(data)
    if "time" in raw.columns:
        raw["time"] = pd.to_datetime(raw["time"].astype("int64"), unit="s", utc=True).dt.tz_localize(None)
    return raw, attrs


# --------------------------------------------------------------------------- 변환
def _source_ref(attrs: dict) -> str:
    parts = []
    for k in ("title", "references", "id"):
        v = attrs.get(k)
        if v and str(v).strip() and str(v).strip() != "TBD":
            parts.append(f"{k}={str(v).strip()}")
    return " | ".join(parts)


def _col(raw: pd.DataFrame, name: str, default=np.nan) -> pd.Series:
    if name in raw.columns:
        return raw[name]
    return pd.Series([default] * len(raw), index=raw.index, dtype="object")


def to_schema(raw: pd.DataFrame, attrs: dict, source_file: str) -> pd.DataFrame:
    """해석된 MARIS 원시 표 → 통합 스키마 DataFrame (핵종 필터·해역 필터 전)."""
    n = len(raw)
    out = pd.DataFrame(index=raw.index)
    out["record_id"] = [schema.make_record_id(SOURCE_DB, source_file, i) for i in raw.index]
    out["source_db"] = SOURCE_DB
    out["source_file"] = source_file
    out["source_row"] = raw.index.astype(int)
    out["source_ref"] = _source_ref(attrs)

    out["cruise"] = pd.NA
    out["station"] = _col(raw, "station", "").astype(str).replace({"": pd.NA})
    idp = _col(raw, "id_provider", "").astype(str)
    mid = _col(raw, "id", "").astype(str)
    out["sample_id"] = np.where(idp.str.strip() != "", idp, mid)

    out["latitude"] = pd.to_numeric(_col(raw, "lat"), errors="coerce")
    out["longitude"] = pd.to_numeric(_col(raw, "lon"), errors="coerce")
    t = pd.to_datetime(_col(raw, "time", pd.NaT), errors="coerce")
    out["sampling_date"] = t.dt.normalize()          # 일 단위. 시각은 아래 notes 에 보존
    out["date_precision"] = "unknown"
    depth = pd.to_numeric(_col(raw, "smp_depth"), errors="coerce")
    out["depth_m"] = depth
    out["depth_type"] = np.where(depth == 0, "surface", "measured")
    region = _col(raw, "area", pd.NA)
    out["region_orig"] = region.where(~region.isin(NA_NAMES), pd.NA) if region.notna().any() else pd.NA

    nuc_name = _col(raw, "nuclide", "").astype(str)
    out["nuclide"] = nuc_name.map(NUCLIDE_MAP)          # 매핑 없으면 NaN → 나중에 제거
    out["value_orig"] = pd.to_numeric(_col(raw, "value"), errors="coerce")
    unit_name = _col(raw, "unit", "NOT AVAILABLE").astype(str)
    out["unit_orig"] = unit_name.map(lambda u: UNIT_NAME_MAP.get(u, u))
    out["unc_orig"] = pd.to_numeric(_col(raw, "unc"), errors="coerce")
    out["unc_type_orig"] = "unknown"
    dl_name = _col(raw, "dl", "Not available").astype(str)
    out["below_dl"] = dl_name.isin(BELOW_DL_NAMES)
    out["dl_value_orig"] = pd.to_numeric(_col(raw, "dlv"), errors="coerce")
    out["ref_date_orig"] = pd.NaT
    cm = _col(raw, "count_met", pd.NA)
    out["method_orig"] = cm.where(~cm.isin(NA_NAMES), pd.NA) if cm.notna().any() else pd.NA

    for c in ("value_bq_m3", "unc_bq_m3", "value_bq_m3_decay"):
        out[c] = np.nan
    out["decay_ref_date"] = pd.NaT
    out["processing_version"] = pd.NA

    temp = pd.to_numeric(_col(raw, "temp"), errors="coerce")
    sal = pd.to_numeric(_col(raw, "sal"), errors="coerce")
    out["temperature_c"] = temp
    out["salinity"] = sal
    out["salinity_scale"] = np.where(sal.notna(), "unknown", None)
    out["ctd_source"] = np.where(temp.notna() | sal.notna(), "paired", "none")
    out["ctd_note"] = np.where(temp.notna() | sal.notna(), "MARIS seawater group sal/temp (same record)", None)

    out["qc_flag"] = "ok"
    notes = []
    filt = _col(raw, "filt", pd.NA)
    lab = _col(raw, "lab", pd.NA)
    tot = pd.to_numeric(_col(raw, "tot_depth"), errors="coerce")
    for i in raw.index:
        bits = [f"maris_nuclide={nuc_name[i]}", f"maris_dl={dl_name[i]}"]
        if pd.notna(t[i]) and t[i] != t[i].normalize():
            bits.append(f"time_utc={t[i].strftime('%H:%M:%S')}")
        if pd.notna(filt[i]) and filt[i] not in NA_NAMES:
            bits.append(f"filtered={filt[i]}")
        if pd.notna(lab[i]) and lab[i] not in NA_NAMES:
            bits.append(f"lab={lab[i]}")
        if pd.notna(tot[i]):
            bits.append(f"tot_depth_m={tot[i]:g}")
        notes.append("; ".join(bits))
    out["notes"] = notes

    out = out[list(schema.COLUMNS)]
    return out.astype({c: t for c, t in schema.COLUMNS.items()})


# --------------------------------------------------------------------------- 파이프라인
def parse(
    path: str | Path,
    pacific_only: bool = True,
    drop_invalid: bool = True,
    lut_dir: Path | None = None,
) -> tuple[pd.DataFrame, dict]:
    """MARIS NetCDF 하나 → (통합 스키마 DataFrame, 처리 보고 dict).

    pacific_only : 태평양 경계상자 또는 MARIS 태평양 해역명에 해당하는 행만 남김
    drop_invalid : 필수값(위경도·날짜·수심·값) 결측 행을 제거하고 보고에 센다
    """
    path = Path(path)
    raw, attrs = read_seawater(path, lut_dir)
    report = {"source_file": path.name, "n_seawater_rows": int(len(raw)), "title": attrs.get("title", "")}
    if raw.empty:
        report.update(n_kept=0, note="no seawater group or empty")
        return schema.empty_frame(), report

    df = to_schema(raw, attrs, path.name)

    # 1) 핵종 필터
    nuc_raw = raw["nuclide"].astype(str) if "nuclide" in raw.columns else pd.Series("", index=raw.index)
    keep = df["nuclide"].notna()
    report["n_dropped_other_nuclides"] = int((~keep).sum())
    report["dropped_nuclide_counts"] = dict(Counter(nuc_raw[~keep]).most_common())
    df, nuc_raw = df[keep], nuc_raw[keep]

    # 2) 해역 필터
    if pacific_only:
        m = pacific_mask(df["latitude"], df["longitude"], df["region_orig"])
        report["n_outside_pacific"] = int((~m).sum())
        df = df[m]

    # 3) 필수값 검사
    if drop_invalid:
        miss = schema.required_missing(df)
        bad = miss.any(axis=1)
        report["n_dropped_invalid"] = int(bad.sum())
        report["invalid_reasons"] = {c: int(miss[c].sum()) for c in schema.REQUIRED if miss[c].any()}
        df = df[~bad]

    df = df.reset_index(drop=True)
    report["n_kept"] = int(len(df))
    report["kept_nuclide_counts"] = df["nuclide"].value_counts().to_dict()
    report["kept_unit_counts"] = df["unit_orig"].value_counts().to_dict()
    report["n_with_ctd"] = int((df["ctd_source"] == "paired").sum())
    if len(df):
        report["time_range"] = [str(df["sampling_date"].min().date()), str(df["sampling_date"].max().date())]
        report["lat_range"] = [float(df["latitude"].min()), float(df["latitude"].max())]
        report["lon_range"] = [float(df["longitude"].min()), float(df["longitude"].max())]
    if drop_invalid and len(df):
        schema.validate(df)
    return df, report


def parse_many(paths, **kw) -> tuple[pd.DataFrame, dict]:
    """여러 MARIS 파일을 이어 붙인다. report 는 파일별 보고 목록과 합계."""
    frames, reports = [], []
    for p in paths:
        df, rep = parse(p, **kw)
        frames.append(df)
        reports.append(rep)
    out = pd.concat(frames, ignore_index=True) if frames else schema.empty_frame()
    summary = {
        "n_files": len(reports),
        "n_kept_total": int(len(out)),
        "kept_nuclide_counts": out["nuclide"].value_counts().to_dict() if len(out) else {},
        "files": reports,
    }
    if len(out):
        schema.validate(out)
    return out, summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="IAEA MARIS NetCDF(seawater) → 통합 스키마 CSV/parquet")
    ap.add_argument("files", nargs="+", help="MARIS NetCDF 파일 경로 (여러 개 가능)")
    ap.add_argument("--out", default="data/processed/maris_pacific_seawater", help="출력 경로 stem (확장자 없이)")
    ap.add_argument("--all-regions", action="store_true", help="태평양 필터를 끄고 전 해역 유지")
    ap.add_argument("--keep-invalid", action="store_true", help="필수값 결측 행을 제거하지 않음 (검증은 생략)")
    a = ap.parse_args(argv)
    df, report = parse_many(a.files, pacific_only=not a.all_regions, drop_invalid=not a.keep_invalid)
    paths = write_processed(df, a.out, report)
    print(json.dumps({k: v for k, v in report.items() if k != "files"}, ensure_ascii=False, indent=2))
    for p in paths:
        print("wrote", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
