"""정답(ground truth)을 아는 합성 표 자료 생성기.

HAMGlobal2021 같은 표 형식 원본을 흉내 낸다. 같은 정답을 두 가지 배치로 렌더링한다.
- wide CSV : 핵종별 열, 연/월/일 분리, 좌표는 십진수·도분 혼합, 값은 "<DL"·"v±u"·별도 오차열 혼합
- long XLSX: 핵종 열 라벨 표기 혼합("Cs-137","137Cs","cs137"…), 제목 행 2줄, 날짜는 문자열·datetime 혼합
"""
from __future__ import annotations

import random
from dataclasses import dataclass

import numpy as np
import pandas as pd

NUCLIDES = ["Cs-137", "Sr-90", "Pu-239+240", "Cs-134", "Pu-240/Pu-239"]
UNITS = {"Cs-137": "Bq/m3", "Sr-90": "Bq/m3", "Pu-239+240": "mBq/m3", "Cs-134": "Bq/m3", "Pu-240/Pu-239": "atom ratio"}
WIDE_HEADER = {"Cs-137": "137Cs (Bq/m3)", "Sr-90": "90Sr (Bq/m3)", "Pu-239+240": "239,240Pu (mBq/m3)",
               "Cs-134": "134Cs (Bq/m3)", "Pu-240/Pu-239": "240Pu/239Pu (atom ratio)"}
LONG_LABELS = {"Cs-137": ["Cs-137", "137Cs", "cs137", "Cs137"], "Sr-90": ["Sr-90", "90Sr"],
               "Pu-239+240": ["Pu-239+240", "239,240Pu", "239+240Pu"], "Cs-134": ["Cs-134", "134Cs"],
               "Pu-240/Pu-239": ["240Pu/239Pu", "Pu-240/Pu-239"]}


@dataclass
class Sample:
    idx: int
    ref: str
    cruise: str
    station: str
    date: pd.Timestamp
    precision: str          # day / month / year
    lat: float
    lon: float
    depth: float
    region: str
    meas: dict              # nuclide -> (value, unc, below_dl)


def make_truth(n: int, seed: int = 0) -> list[Sample]:
    rng = random.Random(seed)
    out = []
    for i in range(n):
        pacific = rng.random() < 0.8
        if pacific:
            lat = round(rng.uniform(-60, 60), 3)
            lon = round(rng.choice([rng.uniform(100, 180), rng.uniform(-180, -70)]), 3)
            region = rng.choice(["North Pacific", "South Pacific", "Japan Sea", ""])
        else:
            lat = round(rng.uniform(30, 60), 3)
            lon = round(rng.uniform(-40, 10), 3)
            region = rng.choice(["North Atlantic", "Baltic", ""])
        y = rng.randint(1956, 2021); mo = rng.randint(1, 12); d = rng.randint(1, 28)
        prec = rng.choices(["day", "month", "year"], [0.8, 0.15, 0.05])[0]
        date = pd.Timestamp(y, mo if prec != "year" else 1, d if prec == "day" else 1)
        depth = rng.choice([0.0, 0.0, 0.0, 10.0, 50.0, 100.0, 500.0, 1000.0, 3000.0])
        meas = {}
        for nuc in NUCLIDES:
            if rng.random() < {"Cs-137": 0.9, "Sr-90": 0.5, "Pu-239+240": 0.35, "Cs-134": 0.15, "Pu-240/Pu-239": 0.1}[nuc]:
                base = {"Cs-137": 3.0, "Sr-90": 2.0, "Pu-239+240": 5.0, "Cs-134": 0.5, "Pu-240/Pu-239": 0.18}[nuc]
                val = round(base * rng.uniform(0.05, 3.0), 4)
                below = rng.random() < 0.08
                unc = round(val * rng.uniform(0.05, 0.3), 4) if (not below and rng.random() < 0.8) else float("nan")
                meas[nuc] = (val, unc, below)
        out.append(Sample(i, f"REF{rng.randint(1, 120):03d}", rng.choice(["KH-68-4", "RF-95", "", "Mirai MR01"]),
                          f"St{rng.randint(1, 400)}", date, prec, lat, lon, depth, region, meas))
    return out


def _coord_str(v: float, kind: str, style: str) -> str:
    if style == "dec":
        return f"{v:.3f}"
    hemi = ("N" if v >= 0 else "S") if kind == "lat" else ("E" if v >= 0 else "W")
    a = abs(v); deg = int(a); minutes = (a - deg) * 60
    if style == "dm":
        return f"{deg} {minutes:.3f} {hemi}"
    return f"{deg}-{minutes:.3f}{hemi}"


def _value_cell(val, unc, below, inline_unc: bool) -> tuple[str, str]:
    """(값 셀, 오차 셀)."""
    if below:
        return f"<{val:g}", ""
    if inline_unc and not np.isnan(unc):
        return f"{val:g}±{unc:g}", ""
    return f"{val:g}", ("" if np.isnan(unc) else f"{unc:g}")


def render_wide_csv(truth: list[Sample], path, seed: int = 1) -> None:
    rng = random.Random(seed)
    cols = ["Ref No", "Cruise", "Station", "Year", "Month", "Day", "Latitude", "Longitude", "Depth (m)", "Region"]
    nuc_cols = []
    for nuc in NUCLIDES:
        nuc_cols += [WIDE_HEADER[nuc], f"{nuc.split('-')[0]}{nuc.split('-')[1].split('/')[0].split('+')[0]} err"]
    rows = []
    for s in truth:
        style = rng.choice(["dec", "dec", "dm", "dms"])
        r = [s.ref, s.cruise, s.station, s.date.year,
             s.date.month if s.precision != "year" else "", s.date.day if s.precision == "day" else "",
             _coord_str(s.lat, "lat", style), _coord_str(s.lon, "lon", style), f"{s.depth:g}", s.region]
        for nuc in NUCLIDES:
            if nuc in s.meas:
                v, u, b = s.meas[nuc]
                vc, uc = _value_cell(v, u, b, inline_unc=(nuc == "Sr-90"))
                r += [vc, uc]
            else:
                r += ["", ""]
        rows.append(r)
    pd.DataFrame(rows, columns=cols + nuc_cols).to_csv(path, index=False)


def render_long_xlsx(truth: list[Sample], path, seed: int = 2) -> None:
    rng = random.Random(seed)
    rows = []
    for s in truth:
        for nuc, (v, u, b) in s.meas.items():
            label = rng.choice(LONG_LABELS[nuc])
            vc, uc = _value_cell(v, u, b, inline_unc=False)
            if s.precision == "day":
                date = s.date.to_pydatetime() if rng.random() < 0.5 else s.date.strftime("%Y/%m/%d")
                y = mo = d = None
            else:
                date = None; y = s.date.year; mo = s.date.month if s.precision == "month" else None; d = None
            rows.append([label, vc, uc, UNITS[nuc], date, y, mo, d, s.lat, s.lon, s.depth, s.ref, s.cruise, s.station, s.region, s.idx])
    cols = ["Nuclide", "Value", "Error", "Unit", "Sampling date", "Year", "Month", "Day", "Lat", "Lon",
            "Sampling depth (m)", "Reference", "Cruise", "Station", "Sea area", "truth_idx"]
    body = pd.DataFrame(rows, columns=cols)
    with pd.ExcelWriter(path) as xw:
        pd.DataFrame([["HAMGlobal-like synthetic sheet"] + [None] * (len(cols) - 1), [None] * len(cols)]).to_excel(
            xw, sheet_name="Data", index=False, header=False)
        body.to_excel(xw, sheet_name="Data", index=False, startrow=2)
        pd.DataFrame({"note": ["readme"]}).to_excel(xw, sheet_name="README", index=False)


def truth_records(truth: list[Sample]) -> pd.DataFrame:
    """정답을 long 형태로 (대조용)."""
    rows = []
    for s in truth:
        for nuc, (v, u, b) in s.meas.items():
            rows.append(dict(idx=s.idx, nuclide=nuc, value=v, unc=u, below_dl=b, unit=UNITS[nuc], date=s.date,
                             precision=s.precision, lat=s.lat, lon=s.lon, depth=s.depth, ref=s.ref, cruise=s.cruise,
                             station=s.station, region=s.region))
    return pd.DataFrame(rows)


def compare_to_truth(df: pd.DataFrame, truth_df: pd.DataFrame, idx_from_row) -> dict:
    """processed df 를 정답과 대조. idx_from_row: processed 행 → 정답 idx 를 주는 함수."""
    mism = []
    seen = set()
    for _, r in df.iterrows():
        idx = idx_from_row(r)
        key = (idx, r["nuclide"])
        t = truth_df[(truth_df.idx == idx) & (truth_df.nuclide == r["nuclide"])]
        if len(t) != 1:
            mism.append({"key": key, "field": "exists", "processed": True, "truth": len(t)}); continue
        t = t.iloc[0]
        if key in seen:
            mism.append({"key": key, "field": "duplicate"}); continue
        seen.add(key)
        def chk(field, a, b, tol=None):
            if (pd.isna(a) and pd.isna(b)):
                return
            ok = (not pd.isna(a)) and (not pd.isna(b)) and (np.isclose(float(a), float(b), atol=tol, rtol=1e-9) if tol is not None else str(a) == str(b))
            if not ok:
                mism.append({"key": key, "field": field, "processed": a, "truth": b})
        chk("value_orig", r["value_orig"], t["value"], 1e-9)
        chk("unc_orig", r["unc_orig"], t["unc"], 1e-9)
        chk("below_dl", bool(r["below_dl"]), bool(t["below_dl"]))
        chk("unit_orig", r["unit_orig"], t["unit"])
        chk("latitude", r["latitude"], t["lat"], 2e-5)     # 도분 소수 3자리 → 1.7e-5°
        chk("longitude", r["longitude"], t["lon"], 2e-5)
        chk("depth_m", r["depth_m"], t["depth"], 1e-9)
        chk("sampling_date", pd.Timestamp(r["sampling_date"]).date(), t["date"].date())
        chk("date_precision", r["date_precision"], t["precision"])
        chk("source_ref", r["source_ref"], t["ref"])
        chk("station", r["station"], t["station"])
        chk("cruise", r["cruise"] if pd.notna(r["cruise"]) else "", t["cruise"])
        chk("region_orig", r["region_orig"] if pd.notna(r["region_orig"]) else "", t["region"])
    missing = set(map(tuple, truth_df[["idx", "nuclide"]].values)) - seen
    return {"n_truth": int(len(truth_df)), "n_processed": int(len(df)), "n_matched": len(seen),
            "n_missing": len(missing), "missing_examples": sorted(missing)[:10], "n_mismatches": len(mism), "mismatches": mism[:30]}
