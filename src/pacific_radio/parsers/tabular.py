"""표 형식(CSV/TSV/XLSX) 원본을 통합 스키마로 바꾸는 공용 엔진.

HAMGlobal2021 처럼 **열 구성을 아직 확인하지 못한** 출처를 위해 만들었다.
1. `inspect_file()` 로 헤더·첫 행·자동 추정 매핑을 본다.
2. 추정 매핑(JSON)을 저장하고 실제 파일에 맞게 고친다.
3. `parse_file(path, mapping=...)` 로 변환한다. 매핑 없이 돌리면 자동 추정을 쓰고 보고서에 남긴다.

지원하는 형식
- wide: 핵종마다 열이 하나씩 ("137Cs (Bq/m3)", "137Cs err", "90Sr", "239,240Pu" …)
- long: 핵종 열 + 값 열 ("Nuclide", "Value", "Error", "Unit")
- 날짜: 한 열(문자열·엑셀 일련번호·yyyymmdd) 또는 Year/Month/Day 분리 열
- 좌표: 십진수, 또는 "35 30 N", "140°30'E", "35-30.5S" 같은 도분초 문자열
- 값: 숫자, "<0.3"(검출한계 미만), "ND", "1.2±0.3"
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from .. import schema
from ..regions import pacific_mask

# --------------------------------------------------------------------------- 헤더 별칭
# 스키마 필드 → 정규화된 헤더 후보 (소문자, 영숫자만). 앞에서부터 우선.
FIELD_ALIASES: dict[str, list[str]] = {
    "latitude": ["latitude", "lat", "latdeg", "latitudedeg", "latitudedecimal", "latdecimal", "ido", "緯度"],
    "longitude": ["longitude", "lon", "long", "lng", "londeg", "longitudedeg", "longitudedecimal", "londecimal", "keido", "経度"],
    "date": ["samplingdate", "sampledate", "date", "datetime", "collectiondate", "sampling", "採取日", "日付"],
    "year": ["year", "yr", "samplingyear", "yyyy", "年"],
    "month": ["month", "mo", "mm", "samplingmonth", "月"],
    "day": ["day", "dd", "samplingday", "日"],
    "depth_m": ["depth", "depthm", "samplingdepth", "sampledepth", "smpdepth", "depthofsampling", "水深", "深度"],
    "bottom_depth": ["bottomdepth", "totdepth", "totaldepth", "waterdepth", "seadepth", "海底水深"],
    "station": ["station", "stn", "st", "stationname", "stationid", "測点"],
    "cruise": ["cruise", "cruisename", "cruiseid", "ship", "vessel", "expedition", "航海"],
    "source_ref": ["reference", "ref", "refid", "refno", "referenceid", "referenceno", "source", "citation", "datasource", "literature", "文献", "出典"],
    "region_orig": ["region", "area", "basin", "sea", "seaarea", "ocean", "box", "海域"],
    "sample_id": ["sampleid", "sampleno", "samplecode", "id", "recordid", "試料番号"],
    "nuclide": ["nuclide", "radionuclide", "isotope", "nuc", "element", "核種"],
    "value": ["value", "activity", "concentration", "conc", "activityconcentration", "activityconc", "result", "濃度"],
    "unc": ["unc", "uncertainty", "error", "err", "sd", "stdev", "sigma", "1sigma", "2sigma", "誤差", "不確かさ"],
    "unit": ["unit", "units", "単位"],
    "ref_date": ["refdate", "referencedate", "decaydate", "decaycorrectiondate", "decaycorrecteddate", "correctiondate", "基準日"],
    "below_dl": ["flag", "dlflag", "detectionflag", "lessthan", "lt", "censored"],
    "temperature_c": ["temperature", "temp", "watertemperature", "sst", "水温"],
    "salinity": ["salinity", "sal", "psu", "塩分"],
}

NUCLIDE_PATTERNS: list[tuple[str, str]] = [
    # (정규화된 라벨에 대한 정규식, 스키마 핵종명). 순서 중요: 합산/비율을 단일 핵종보다 먼저.
    (r"^(pu)?240(pu)?/(pu)?239(pu)?$|^pu240pu239|^240pu239pu|240/239", "Pu-240/Pu-239"),
    (r"^(pu)?238(pu)?/(pu)?239[,+]?240(pu)?$|pu238pu239240|238pu239240pu|238/239[,+]?240", "Pu-238/Pu-239+240"),
    (r"^(pu)?239[,+/]?240(pu)?$|^pu239240$|^239240pu$|^pu\(?239\+?240\)?$|^pu239\+240$|^239\+240pu$|^239,240pu$|^pu239,240$", "Pu-239+240"),
    (r"^(cs)?137(cs)?$|^cs137$|^137cs$|^caesium137$|^cesium137$", "Cs-137"),
    (r"^(cs)?134(cs)?$|^cs134$|^134cs$", "Cs-134"),
    (r"^(sr)?90(sr)?$|^sr90$|^90sr$|^strontium90$", "Sr-90"),
    (r"^(pu)?238(pu)?$|^pu238$|^238pu$", "Pu-238"),
    (r"^(pu)?239(pu)?$|^pu239$|^239pu$", "Pu-239"),
    (r"^(pu)?240(pu)?$|^pu240$|^240pu$", "Pu-240"),
    (r"^(pu)?241(pu)?$|^pu241$|^241pu$", "Pu-241"),
    # 대상 외 핵종: 인식은 하되 버린다 (보고서에 집계)
    (r"^(h)?3(h)?$|^h3$|^3h$|^tritium$", "OTHER:H-3"),
    (r"^(am)?241(am)?$|^am241$|^241am$", "OTHER:Am-241"),
    (r"^(c)?14(c)?$|^c14$|^14c$", "OTHER:C-14"),
    (r"^(sr)?89(sr)?$|^sr89$|^89sr$", "OTHER:Sr-89"),
    (r"^(i)?129(i)?$|^i129$|^129i$", "OTHER:I-129"),
]
UNC_HINTS = ("err", "unc", "sd", "stdev", "sigma", "±", "error", "1s", "2s", "uncertainty", "誤差")
MISSING_TOKENS = {"", "-", "--", "na", "n/a", "nan", "none", "null", "nd", "n.d.", "n.d", "nd.", "bdl", "mdl", "<dl", "<mdl"}
ND_TOKENS = {"nd", "n.d.", "n.d", "nd.", "bdl", "<dl", "<mdl", "mdl"}


def norm(s) -> str:
    """헤더 정규화: 소문자, 괄호 내용 제거, 영숫자·+,/ 만 남김."""
    s = str(s)
    s = re.sub(r"[\(\[\{].*?[\)\]\}]", "", s)
    return re.sub(r"[^a-z0-9+,/一-龥ぁ-んァ-ン]", "", s.lower())


def header_unit(header) -> str | None:
    """헤더의 괄호 안 단위 ("137Cs (Bq/m3)" → "Bq/m3")."""
    m = re.search(r"[\(\[\{]\s*([^\)\]\}]*?)\s*[\)\]\}]", str(header))
    if not m:
        return None
    u = m.group(1).strip()
    return u if re.search(r"bq|ci|tu|ratio|atom|dpm|pci|%", u.lower()) else None


def nuclide_from_label(label) -> str | None:
    """헤더/셀 라벨에서 핵종명. 대상 외는 'OTHER:…', 핵종이 아니면 None."""
    n = norm(label)
    suffix = r"(atomratio|activityratio|ratio|atom|err|error|unc|uncertainty|sd|stdev|sigma|1s|2s|value|activity|conc|concentration|bq|m3|kg|l)$"
    while True:                                          # 꼬리말을 반복해서 벗긴다 ("pu240/pu239atomratio" → "pu240/pu239")
        n2 = re.sub(suffix, "", n)
        if n2 == n:
            break
        n = n2
    n = n.strip("+,/")
    if not n:
        return None
    for pat, name in NUCLIDE_PATTERNS:
        if re.search(pat, n):
            return name
    return None


def is_unc_label(label) -> bool:
    n = str(label).lower()
    return any(h in n for h in UNC_HINTS)


# --------------------------------------------------------------------------- 셀 파서
_COORD_RE = re.compile(r"\d+(?:\.\d+)?")


def parse_coord(x, kind: str) -> float:
    """위도/경도 셀 → 십진수. kind 는 'lat' 또는 'lon'. 실패 시 NaN."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return np.nan
    if isinstance(x, (int, float, np.integer, np.floating)):
        return float(x)
    s = str(x).strip().upper().replace("，", ",")
    if s in MISSING_TOKENS:
        return np.nan
    hemi = None
    m = re.search(r"([NSEW])", s)
    if m:
        hemi = m.group(1)
    nums = _COORD_RE.findall(s)
    if not nums:
        return np.nan
    deg = float(nums[0])
    mnt = float(nums[1]) if len(nums) > 1 else 0.0
    sec = float(nums[2]) if len(nums) > 2 else 0.0
    sign = -1.0 if s.startswith("-") else 1.0          # 숫자 사이의 '-' 는 도/분 구분자, 맨 앞의 '-' 만 부호
    val = deg + mnt / 60.0 + sec / 3600.0
    if hemi in ("S", "W"):
        sign = -1.0
    return sign * val


def parse_value(x) -> tuple[float, float, bool]:
    """농도 셀 → (값, 불확도, 검출한계미만). 'ND' → (NaN, NaN, True), '<0.3' → (0.3, NaN, True)."""
    if x is None:
        return np.nan, np.nan, False
    if isinstance(x, (int, float, np.integer, np.floating)):
        return (np.nan, np.nan, False) if (isinstance(x, float) and np.isnan(x)) else (float(x), np.nan, False)
    s = str(x).strip().replace("，", ",").replace(" ", "")
    low = s.lower()
    if low in ND_TOKENS:
        return np.nan, np.nan, True
    if low in MISSING_TOKENS:
        return np.nan, np.nan, False
    below = False
    if s.startswith(("<", "≤", "<=")):
        below = True
        s = s.lstrip("<≤=")
    m = re.match(r"^([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)(?:(?:±|\+/-|\+-|\+\/\-)([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?))?$", s.replace(",", ""))
    if not m:
        return np.nan, np.nan, below
    val = float(m.group(1))
    unc = float(m.group(2)) if m.group(2) else np.nan
    return val, unc, below


def parse_dates(df: pd.DataFrame, cols: dict) -> tuple[pd.Series, pd.Series]:
    """날짜 열 또는 Year/Month/Day 열 → (datetime Series, precision Series)."""
    n = len(df)
    if cols.get("date") in df.columns:
        raw = df[cols["date"]]
        dt = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")
        num = pd.to_numeric(raw, errors="coerce")
        # yyyymmdd 정수
        m8 = num.notna() & (num >= 19000101) & (num <= 21001231)
        if m8.any():
            dt[m8] = pd.to_datetime(num[m8].astype("int64").astype(str), format="%Y%m%d", errors="coerce")
        # 엑셀 일련번호
        mx = num.notna() & (num >= 10000) & (num < 80000)
        if mx.any():
            dt[mx] = pd.to_datetime(num[mx], unit="D", origin="1899-12-30", errors="coerce")
        rest = dt.isna() & raw.notna()
        if rest.any():
            try:
                dt[rest] = pd.to_datetime(raw[rest], errors="coerce", format="mixed")
            except (ValueError, TypeError):
                dt[rest] = pd.to_datetime(raw[rest], errors="coerce")
        prec = pd.Series(np.where(dt.notna(), "day", None), index=df.index, dtype="object")
        return dt, prec
    if cols.get("year") in df.columns:
        y = pd.to_numeric(df[cols["year"]], errors="coerce")
        mo = pd.to_numeric(df[cols["month"]], errors="coerce") if cols.get("month") in df.columns else pd.Series(np.nan, index=df.index)
        d = pd.to_numeric(df[cols["day"]], errors="coerce") if cols.get("day") in df.columns else pd.Series(np.nan, index=df.index)
        prec = pd.Series(np.where(d.notna(), "day", np.where(mo.notna(), "month", np.where(y.notna(), "year", None))), index=df.index, dtype="object")
        frame = pd.DataFrame({"year": y, "month": mo.fillna(1), "day": d.fillna(1)})
        dt = pd.to_datetime(frame, errors="coerce")
        return dt, prec
    return pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]"), pd.Series(None, index=df.index, dtype="object")


# --------------------------------------------------------------------------- 파일 읽기
def load_tables(path: str | Path, sheet=None, header_row: int | None = None) -> list[tuple[str, pd.DataFrame]]:
    """CSV/TSV/TXT/XLS(X) → [(표 이름, DataFrame)]. 엑셀은 모든 시트(또는 지정 시트)."""
    path = Path(path)
    suf = path.suffix.lower()
    if suf in (".xlsx", ".xlsm", ".xls"):
        sheets = pd.read_excel(path, sheet_name=sheet if sheet is not None else None, header=None, dtype=object)
        if isinstance(sheets, pd.DataFrame):
            sheets = {str(sheet): sheets}
        out = []
        for name, raw in sheets.items():
            df = _apply_header(raw, header_row)
            if len(df.columns) >= 3 and len(df) > 0:
                out.append((str(name), df))
        return out
    sep = "\t" if suf in (".tsv", ".txt") else None
    for enc in ("utf-8-sig", "cp932", "euc-kr", "latin-1"):
        try:
            raw = pd.read_csv(path, sep=sep, header=None, dtype=object, engine="python", encoding=enc, skip_blank_lines=True)
            break
        except UnicodeDecodeError:
            continue
    return [(path.stem, _apply_header(raw, header_row))]


def _apply_header(raw: pd.DataFrame, header_row: int | None) -> pd.DataFrame:
    """헤더 행을 찾아 열 이름으로 쓴다. 지정이 없으면 '문자열 셀이 가장 많은 상위 20행 중 첫 행'."""
    if raw.empty:
        return raw
    if header_row is None:
        best, best_score = 0, -1
        for i in range(min(20, len(raw))):
            row = raw.iloc[i]
            strs = sum(isinstance(v, str) and not re.fullmatch(r"[-+\d.,eE<>± ]+", v.strip()) for v in row if pd.notna(v))
            if strs > best_score and strs >= max(3, 0.5 * row.notna().sum()):
                best, best_score = i, strs
                break
        header_row = best
    header = [str(v).strip() if pd.notna(v) else f"col{j}" for j, v in enumerate(raw.iloc[header_row])]
    df = raw.iloc[header_row + 1:].copy()
    df.columns = header
    df = df.dropna(how="all").reset_index(drop=True)
    return df


# --------------------------------------------------------------------------- 매핑 추정
def guess_mapping(columns) -> dict:
    """열 이름 목록 → 매핑 dict (JSON 저장 가능). 사람이 확인·수정하는 것을 전제로 한다."""
    cols = [str(c) for c in columns]
    normed = {c: norm(c) for c in cols}
    mapping: dict = {"columns": {}, "nuclide_columns": {}, "default_unit": None, "notes_columns": []}
    used = set()

    # 1) 핵종 열 (wide) 과 그 불확도 열
    last_nuc_col = None
    for c in cols:
        nuc = nuclide_from_label(c)
        if nuc and not is_unc_label(c):
            mapping["nuclide_columns"][c] = {"nuclide": nuc, "unit": header_unit(c), "unc_column": None}
            used.add(c)
            last_nuc_col = c
        elif is_unc_label(c) and (nuc or last_nuc_col):
            target = c if nuc else last_nuc_col
            # 핵종이 적힌 불확도 열은 같은 핵종의 값 열에, 아니면 직전 값 열에 붙인다
            if nuc:
                target = next((k for k, v in mapping["nuclide_columns"].items() if v["nuclide"] == nuc and v["unc_column"] is None), None)
            if target and target in mapping["nuclide_columns"]:
                mapping["nuclide_columns"][target]["unc_column"] = c
                used.add(c)

    # 2) 일반 필드
    for field, aliases in FIELD_ALIASES.items():
        for a in aliases:
            hit = next((c for c in cols if c not in used and normed[c] == a), None)
            if hit:
                mapping["columns"][field] = hit
                used.add(hit)
                break

    # long 형식이면 핵종 열 매핑은 비운다 (값 열과 함께 쓰므로)
    if "nuclide" in mapping["columns"] and "value" in mapping["columns"]:
        mapping["format"] = "long"
    elif mapping["nuclide_columns"]:
        mapping["format"] = "wide"
    else:
        mapping["format"] = "unknown"
    mapping["unmapped_columns"] = [c for c in cols if c not in used]
    return mapping


def inspect_file(path: str | Path, sheet=None, header_row: int | None = None, n_rows: int = 5) -> dict:
    """헤더, 첫 행, 추정 매핑을 dict 로. CLI --inspect 가 JSON 으로 출력한다."""
    out = {"file": str(path), "tables": []}
    for name, df in load_tables(path, sheet, header_row):
        out["tables"].append({
            "table": name,
            "n_rows": int(len(df)),
            "columns": [str(c) for c in df.columns],
            "head": df.head(n_rows).astype(str).to_dict(orient="records"),
            "guessed_mapping": guess_mapping(df.columns),
        })
    return out


# --------------------------------------------------------------------------- 변환
def table_to_schema(df: pd.DataFrame, mapping: dict, source_db: str, source_file: str,
                    default_unit: str | None = None) -> tuple[pd.DataFrame, dict]:
    """한 표 → 통합 스키마 (핵종·해역 필터 전). 보고 dict 에 버린 핵종 집계."""
    cols = mapping.get("columns", {})
    fmt = mapping.get("format") or ("long" if "nuclide" in cols and "value" in cols else "wide")
    default_unit = default_unit or mapping.get("default_unit")
    n = len(df)
    base = pd.DataFrame(index=df.index)
    base["latitude"] = [parse_coord(v, "lat") for v in df[cols["latitude"]]] if cols.get("latitude") in df.columns else np.nan
    base["longitude"] = [parse_coord(v, "lon") for v in df[cols["longitude"]]] if cols.get("longitude") in df.columns else np.nan
    dt, prec = parse_dates(df, cols)
    base["sampling_date"], base["date_precision"] = dt, prec
    base["depth_m"] = pd.to_numeric(df[cols["depth_m"]], errors="coerce") if cols.get("depth_m") in df.columns else np.nan
    for f in ("station", "cruise", "source_ref", "region_orig", "sample_id"):
        base[f] = df[cols[f]].astype(str).str.strip().replace({"": None, "nan": None}) if cols.get(f) in df.columns else None
    base["ref_date_orig"] = parse_dates(df, {"date": cols["ref_date"]})[0] if cols.get("ref_date") in df.columns else pd.NaT
    base["temperature_c"] = pd.to_numeric(df[cols["temperature_c"]], errors="coerce") if cols.get("temperature_c") in df.columns else np.nan
    base["salinity"] = pd.to_numeric(df[cols["salinity"]], errors="coerce") if cols.get("salinity") in df.columns else np.nan
    bottom = pd.to_numeric(df[cols["bottom_depth"]], errors="coerce") if cols.get("bottom_depth") in df.columns else pd.Series(np.nan, index=df.index)
    extra_notes = [c for c in mapping.get("notes_columns", []) if c in df.columns]

    records = []
    dropped = Counter()
    if fmt == "long":
        unit_col = cols.get("unit") if cols.get("unit") in df.columns else None
        unc_col = cols.get("unc") if cols.get("unc") in df.columns else None
        for i in df.index:
            nuc = nuclide_from_label(df.at[i, cols["nuclide"]])
            if nuc is None or nuc.startswith("OTHER:"):
                dropped[str(df.at[i, cols["nuclide"]])] += 1
                continue
            val, unc_in, below = parse_value(df.at[i, cols["value"]])
            unc = parse_value(df.at[i, unc_col])[0] if unc_col else np.nan
            unc = unc if pd.notna(unc) else unc_in
            unit = str(df.at[i, unit_col]).strip() if unit_col and pd.notna(df.at[i, unit_col]) else (default_unit or "UNKNOWN")
            records.append((i, nuc, val, unc, below, unit, cols["value"]))
    else:
        for col, spec in mapping.get("nuclide_columns", {}).items():
            if col not in df.columns:
                continue
            nuc = spec["nuclide"]
            if nuc.startswith("OTHER:"):
                dropped[col] += int(df[col].notna().sum())
                continue
            unit = spec.get("unit") or default_unit or "UNKNOWN"
            ucol = spec.get("unc_column") if spec.get("unc_column") in df.columns else None
            for i in df.index:
                cell = df.at[i, col]
                if pd.isna(cell) or str(cell).strip() == "":
                    continue
                val, unc_in, below = parse_value(cell)
                if np.isnan(val) and not below:
                    continue
                unc = parse_value(df.at[i, ucol])[0] if ucol else np.nan
                unc = unc if pd.notna(unc) else unc_in
                records.append((i, nuc, val, unc, below, unit, col))

    if not records:
        return schema.empty_frame(), {"dropped_nuclide_counts": dict(dropped), "format": fmt}

    idx = [r[0] for r in records]
    out = pd.DataFrame(index=range(len(records)))
    out["record_id"] = [schema.make_record_id(source_db, source_file, int(i)) + f":{r[6]}" for i, r in zip(idx, records)]
    out["source_db"] = source_db
    out["source_file"] = source_file
    out["source_row"] = [int(i) for i in idx]
    b = base.loc[idx].reset_index(drop=True)
    out["source_ref"] = b["source_ref"]
    out["cruise"], out["station"], out["sample_id"] = b["cruise"], b["station"], b["sample_id"]
    out["latitude"], out["longitude"] = b["latitude"], b["longitude"]
    out["sampling_date"] = b["sampling_date"]
    out["date_precision"] = b["date_precision"].fillna("unknown")
    out["depth_m"] = b["depth_m"]
    out["depth_type"] = np.where(b["depth_m"] == 0, "surface", np.where(b["depth_m"].notna(), "measured", None))
    out["region_orig"] = b["region_orig"]
    out["nuclide"] = [r[1] for r in records]
    out["value_orig"] = [r[2] for r in records]
    out["unit_orig"] = [r[5] for r in records]
    out["unc_orig"] = [r[3] for r in records]
    out["unc_type_orig"] = "unknown"
    out["below_dl"] = [bool(r[4]) for r in records]
    out["dl_value_orig"] = np.nan
    out["ref_date_orig"] = b["ref_date_orig"]
    out["method_orig"] = None
    for c in ("value_bq_m3", "unc_bq_m3", "value_bq_m3_decay"):
        out[c] = np.nan
    out["decay_ref_date"] = pd.NaT
    out["processing_version"] = None
    out["temperature_c"], out["salinity"] = b["temperature_c"], b["salinity"]
    has_ctd = b["temperature_c"].notna() | b["salinity"].notna()
    out["salinity_scale"] = np.where(b["salinity"].notna(), "unknown", None)
    out["ctd_source"] = np.where(has_ctd, "paired", "none")
    out["ctd_note"] = np.where(has_ctd, f"{source_db} same row", None)
    out["qc_flag"] = "ok"
    notes = []
    for i, r in zip(idx, records):
        bits = [f"src_column={r[6]}"]
        if pd.notna(bottom.at[i]):
            bits.append(f"bottom_depth_m={bottom.at[i]:g}")
        for c in extra_notes:
            v = df.at[i, c]
            if pd.notna(v) and str(v).strip():
                bits.append(f"{c}={str(v).strip()}")
        notes.append("; ".join(bits))
    out["notes"] = notes
    out = out[list(schema.COLUMNS)].astype({c: t for c, t in schema.COLUMNS.items()})
    return out, {"dropped_nuclide_counts": dict(dropped), "format": fmt}


def parse_file(path: str | Path, source_db: str, mapping: dict | None = None, sheet=None,
               header_row: int | None = None, pacific_only: bool = True, drop_invalid: bool = True,
               default_unit: str | None = None) -> tuple[pd.DataFrame, dict]:
    """파일 하나(모든 시트) → (통합 스키마 DataFrame, 보고)."""
    path = Path(path)
    tables = load_tables(path, sheet if sheet is not None else (mapping or {}).get("sheet"),
                         header_row if header_row is not None else (mapping or {}).get("header_row"))
    frames, treports = [], []
    for name, df in tables:
        m = mapping or guess_mapping(df.columns)
        sf = path.name if len(tables) == 1 else f"{path.name}::{name}"
        out, rep = table_to_schema(df, m, source_db, sf, default_unit)
        rep.update(table=name, n_rows_in=int(len(df)), n_records=int(len(out)), mapping_used=("given" if mapping else "guessed"),
                   unmapped_columns=m.get("unmapped_columns", []))
        frames.append(out)
        treports.append(rep)
    df = pd.concat(frames, ignore_index=True) if frames else schema.empty_frame()
    report: dict = {"source_file": path.name, "tables": treports, "n_records_before_filters": int(len(df))}
    if pacific_only and len(df):
        m = pacific_mask(df["latitude"], df["longitude"], df["region_orig"])
        report["n_outside_pacific"] = int((~m).sum())
        df = df[m]
    if drop_invalid and len(df):
        miss = schema.required_missing(df)
        bad = miss.any(axis=1)
        report["n_dropped_invalid"] = int(bad.sum())
        report["invalid_reasons"] = {c: int(miss[c].sum()) for c in schema.REQUIRED if miss[c].any()}
        df = df[~bad]
    df = df.reset_index(drop=True)
    report["n_kept"] = int(len(df))
    report["kept_nuclide_counts"] = df["nuclide"].value_counts().to_dict()
    report["kept_unit_counts"] = df["unit_orig"].value_counts().to_dict()
    report["n_unit_unknown"] = int((df["unit_orig"] == "UNKNOWN").sum())
    if len(df):
        report["time_range"] = [str(df["sampling_date"].min().date()), str(df["sampling_date"].max().date())]
    if drop_invalid and len(df):
        schema.validate(df)
    return df, report


def load_mapping(path: str | Path | None) -> dict | None:
    if not path:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))
