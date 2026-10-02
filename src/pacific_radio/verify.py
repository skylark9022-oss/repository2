"""변환 결과 대조 검증 (reconciliation).

파서 코드를 쓰지 않고 원본을 따로 읽어, data/processed/ 의 각 행이 원본 값과 일치하는지 확인한다.
- reconcile_maris : MARIS NetCDF 를 netCDF4 로 직접 읽어 행 단위 대조 (코드 해석은 파일 enum + LUT CSV 로 독립 수행)
- reconcile_tabular: 표 원본의 셀을 source_row + notes 의 src_column 으로 찾아 숫자 셀은 자동 대조, 문자 셀은 나란히 출력
- roundtrip_check  : write_processed → read_processed 왕복에서 값이 보존되는지
- accounting_check : 원본 행 수 = 유지 + 대상외 핵종 + 해역 외 + 필수값 결측

명령줄
  python -m pacific_radio.verify maris   <원본.nc>  <processed.csv>
  python -m pacific_radio.verify tabular <원본.csv|xlsx> <processed.csv> [--map column_map.json]
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

import netCDF4 as nc
import numpy as np
import pandas as pd

from . import schema
from .store import read_processed, write_processed

# 파서와 독립적으로 MARIS 코드 → 스키마 핵종명 (dbo_nuclide.csv 의 nuclide_id 기준)
MARIS_NUCLIDE_CODE = {12: "Sr-90", 31: "Cs-134", 33: "Cs-137", 67: "Pu-238", 68: "Pu-239", 69: "Pu-240",
                      70: "Pu-241", 77: "Pu-239+240", 141: "Pu-240/Pu-239", 81: "Pu-238/Pu-239+240"}
MARIS_BELOW_DL_CODES = {2, 3}


def _eq(a, b, rtol=1e-6, atol=1e-9) -> bool:
    """NaN==NaN 을 참으로 보는 수치/문자 비교."""
    if a is None or b is None or (isinstance(a, float) and math.isnan(a)) or (isinstance(b, float) and math.isnan(b)):
        an = a is None or (isinstance(a, float) and math.isnan(a)) or a is pd.NA or a is pd.NaT
        bn = b is None or (isinstance(b, float) and math.isnan(b)) or b is pd.NA or b is pd.NaT
        return an and bn
    if isinstance(a, (int, float, np.number)) and isinstance(b, (int, float, np.number)):
        return bool(np.isclose(float(a), float(b), rtol=rtol, atol=atol))
    return str(a) == str(b)


def _lut(lut_dir: Path, fname: str, key: str, val: str) -> dict:
    t = pd.read_csv(lut_dir / fname)
    return dict(zip(t[key].astype(int), t[val].astype(str)))


# --------------------------------------------------------------------------- MARIS
def read_maris_raw_independent(path: str | Path, lut_dir: Path) -> pd.DataFrame:
    """seawater 그룹을 '코드 그대로' 읽고, 이름 해석은 파일 enum → 없으면 LUT CSV."""
    with nc.Dataset(path) as ds:
        g = ds.groups["seawater"]
        def get(name):
            if name not in g.variables:
                return None
            v = g.variables[name][:]
            return v
        n = len(g.variables["value"][:])
        raw = pd.DataFrame(index=range(n))
        for name in ("lat", "lon", "smp_depth", "value", "unc", "dlv", "sal", "temp"):
            v = get(name)
            raw[name] = np.ma.filled(v, np.nan).astype(float) if v is not None else np.nan
        raw["time"] = np.ma.filled(get("time"), 0).astype("int64")
        for name in ("nuclide", "unit", "dl"):
            v = get(name)
            raw[name + "_code"] = np.ma.filled(v, -1).astype("int64") if v is not None else -1
        unit_names = _lut(lut_dir, "dbo_unit.csv", "unit_id", "unit")
        var = g.variables["unit"]
        if isinstance(var.datatype, nc.EnumType):   # 파일 enum 이름 → dbo_unit.unit 문자열로 재해석
            inv = {v: k for k, v in var.datatype.enum_dict.items()}
            san = _lut(lut_dir, "dbo_unit.csv", "unit_id", "unit_sanitized")
            san_to_unit = {san[k]: unit_names[k] for k in san}
            raw["unit_name"] = [san_to_unit.get(inv.get(int(c), ""), inv.get(int(c), "?")) for c in raw["unit_code"]]
        else:
            raw["unit_name"] = [unit_names.get(int(c), "?") for c in raw["unit_code"]]
        raw["station"] = [str(s) for s in np.asarray(get("station"))] if get("station") is not None else ""
    raw["nuclide_name"] = raw["nuclide_code"].map(MARIS_NUCLIDE_CODE)
    raw["below_dl"] = raw["dl_code"].isin(MARIS_BELOW_DL_CODES)
    raw["date"] = pd.to_datetime(raw["time"], unit="s").dt.normalize()
    return raw


def reconcile_maris(nc_path: str | Path, processed: pd.DataFrame, lut_dir: Path | None = None) -> dict:
    """processed 의 각 행을 원본 행(source_row)과 대조. 반환: 요약 + 불일치 목록."""
    nc_path = Path(nc_path)
    lut_dir = lut_dir or Path(__file__).resolve().parents[2] / "data" / "external" / "maris_lut"
    raw = read_maris_raw_independent(nc_path, lut_dir)
    proc = processed[processed["source_file"] == nc_path.name]
    checks = {"latitude": "lat", "longitude": "lon", "depth_m": "smp_depth", "value_orig": "value",
              "unc_orig": "unc", "dl_value_orig": "dlv", "salinity": "sal", "temperature_c": "temp"}
    mismatches, n_compared = [], 0
    for _, row in proc.iterrows():
        i = int(row["source_row"])
        r = raw.loc[i]
        n_compared += 1
        for pc, rc in checks.items():
            a = row[pc]; b = r[rc]
            a = float(a) if pd.notna(a) else float("nan")
            if not _eq(a, b):
                mismatches.append({"source_row": i, "field": pc, "processed": a, "raw": b})
        if str(row["nuclide"]) != str(r["nuclide_name"]):
            mismatches.append({"source_row": i, "field": "nuclide", "processed": row["nuclide"], "raw": r["nuclide_name"]})
        if str(row["unit_orig"]) != str(r["unit_name"]):
            mismatches.append({"source_row": i, "field": "unit_orig", "processed": row["unit_orig"], "raw": r["unit_name"]})
        if bool(row["below_dl"]) != bool(r["below_dl"]):
            mismatches.append({"source_row": i, "field": "below_dl", "processed": bool(row["below_dl"]), "raw": bool(r["below_dl"])})
        if pd.Timestamp(row["sampling_date"]) != r["date"]:
            mismatches.append({"source_row": i, "field": "sampling_date", "processed": str(row["sampling_date"]), "raw": str(r["date"])})
        if r["station"] and str(row["station"]) != r["station"]:
            mismatches.append({"source_row": i, "field": "station", "processed": row["station"], "raw": r["station"]})
    # 계정 검사: 대상 핵종이면서 필수값이 있는 원본 행은 (해역 필터가 없을 때) 전부 들어와야 한다
    target = raw["nuclide_name"].notna()
    required_ok = raw["lat"].notna() & raw["lon"].notna() & raw["smp_depth"].notna() & (raw["value"].notna() | raw["below_dl"])
    expected_all_regions = int((target & required_ok).sum())
    return {
        "file": nc_path.name, "n_raw_rows": int(len(raw)), "n_raw_target_nuclide": int(target.sum()),
        "n_expected_if_all_regions": expected_all_regions, "n_processed_rows": int(len(proc)),
        "n_compared": n_compared, "n_fields_checked_per_row": len(checks) + 5,
        "n_mismatches": len(mismatches), "mismatches": mismatches[:50],
        "missing_source_rows": sorted(set(raw.index[target & required_ok]) - set(proc["source_row"].astype(int))) [:50],
    }


# --------------------------------------------------------------------------- 표 형식
_NUM = re.compile(r"^[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?$")


def reconcile_tabular(src_path: str | Path, processed: pd.DataFrame, mapping: dict | None = None,
                      sheet=None, header_row: int | None = None) -> dict:
    """표 원본 셀과 processed 값을 나란히 대조. 숫자 셀은 자동 판정, 그 외는 manual_review 목록으로."""
    from .parsers.tabular import load_tables   # 표 읽기(헤더 탐지)만 공유. 셀 해석은 여기서 독립 수행
    src_path = Path(src_path)
    tables = dict(load_tables(src_path, sheet if sheet is not None else (mapping or {}).get("sheet"),
                              header_row if header_row is not None else (mapping or {}).get("header_row")))
    mismatches, manual, n_auto = [], [], 0
    proc = processed[processed["source_file"].str.startswith(src_path.name)]
    for _, row in proc.iterrows():
        sf = str(row["source_file"])
        tname = sf.split("::", 1)[1] if "::" in sf else next(iter(tables))
        df = tables[tname]
        i = int(row["source_row"])
        m = re.search(r"src_column=([^;]+)", str(row["notes"]))
        col = m.group(1).strip() if m else None
        if col is None or col not in df.columns or i not in df.index:
            mismatches.append({"source_row": i, "field": "locate", "processed": col, "raw": None})
            continue
        cell = df.at[i, col]
        cs = str(cell).strip().replace(",", "") if pd.notna(cell) else ""
        pv = row["value_orig"]
        if _NUM.match(cs):
            n_auto += 1
            if not (pd.notna(pv) and np.isclose(float(cs), float(pv), rtol=1e-9)):
                mismatches.append({"source_row": i, "field": "value_orig", "processed": pv, "raw": cs, "column": col})
        else:
            manual.append({"source_row": i, "column": col, "cell": cs, "value_orig": None if pd.isna(pv) else float(pv),
                           "unc_orig": None if pd.isna(row["unc_orig"]) else float(row["unc_orig"]), "below_dl": bool(row["below_dl"])})
        # 좌표: 숫자 셀만 자동 대조
        cols = (mapping or {}).get("columns", {})
        for field, key in (("latitude", "latitude"), ("longitude", "longitude"), ("depth_m", "depth_m")):
            c = cols.get(key)
            if c and c in df.columns:
                v = df.at[i, c]; vs = str(v).strip() if pd.notna(v) else ""
                if _NUM.match(vs):
                    n_auto += 1
                    if not np.isclose(float(vs), float(row[field]), rtol=1e-9, atol=1e-9):
                        mismatches.append({"source_row": i, "field": field, "processed": float(row[field]), "raw": vs})
    return {"file": src_path.name, "n_processed_rows": int(len(proc)), "n_auto_checked_cells": n_auto,
            "n_mismatches": len(mismatches), "mismatches": mismatches[:50],
            "n_manual_review": len(manual), "manual_review": manual[:50]}


# --------------------------------------------------------------------------- 공통
def roundtrip_check(df: pd.DataFrame, stem: str | Path) -> dict:
    """저장 → 재읽기 후 모든 셀이 같은지. 날짜는 일 단위, 실수는 상대오차 1e-12."""
    paths = write_processed(df, stem)
    out = {"paths": [str(p) for p in paths], "n_rows": int(len(df)), "mismatch_cells": []}
    for p in paths:
        if p.suffix not in (".csv", ".parquet"):
            continue
        back = read_processed(p)
        if len(back) != len(df):
            out["mismatch_cells"].append({"file": p.name, "field": "__len__", "a": len(df), "b": len(back)})
            continue
        for c, t in schema.COLUMNS.items():
            a, b = df[c].reset_index(drop=True), back[c].reset_index(drop=True)
            if t.startswith("float"):
                bad = ~(np.isclose(a.astype(float), b.astype(float), rtol=1e-12, equal_nan=True))
            elif t.startswith("datetime"):
                bad = ~((a.isna() & b.isna()) | (pd.to_datetime(a).dt.normalize() == pd.to_datetime(b).dt.normalize()))
            else:
                bad = ~((a.isna() & b.isna()) | (a.astype("string").fillna("<NA>") == b.astype("string").fillna("<NA>")))
            n = int(bad.sum())
            if n:
                out["mismatch_cells"].append({"file": p.name, "field": c, "n": n, "example_a": str(a[bad].iloc[0]), "example_b": str(b[bad].iloc[0])})
    out["ok"] = not out["mismatch_cells"]
    return out


def accounting_check(report: dict) -> dict:
    """파서 보고서의 수치가 서로 맞는지 (원본 = 유지 + 제외 사유별 합)."""
    n_in = report.get("n_seawater_rows", report.get("n_records_before_filters"))
    parts = {k: report.get(k, 0) for k in ("n_kept", "n_dropped_other_nuclides", "n_outside_pacific", "n_dropped_invalid")}
    total = sum(parts.values())
    return {"n_in": n_in, **parts, "sum": total, "ok": (n_in is None) or (n_in == total)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="원본 ↔ processed 대조 검증")
    ap.add_argument("kind", choices=["maris", "tabular"])
    ap.add_argument("source")
    ap.add_argument("processed")
    ap.add_argument("--map")
    a = ap.parse_args(argv)
    proc = read_processed(a.processed)
    if a.kind == "maris":
        res = reconcile_maris(a.source, proc)
    else:
        mapping = json.loads(Path(a.map).read_text(encoding="utf-8")) if a.map else None
        res = reconcile_tabular(a.source, proc, mapping)
    print(json.dumps(res, ensure_ascii=False, indent=2, default=str))
    return 0 if res["n_mismatches"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
