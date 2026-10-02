"""표 형식 엔진(tabular.py)과 HAMGlobal2021 래퍼 테스트.

HAMGlobal2021 실제 파일은 없으므로, 있을 법한 두 가지 배치(wide CSV, long XLSX)를 합성해 검사한다.
실제 파일을 받으면 tests/data/ 에 작은 발췌본을 넣고 이 테스트를 보강할 것.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pacific_radio import schema
from pacific_radio.parsers import hamglobal, tabular


# ------------------------------------------------------------------ 셀 파서
@pytest.mark.parametrize("x,kind,exp", [
    (35.5, "lat", 35.5), ("35.5", "lat", 35.5), ("35.5N", "lat", 35.5), ("35 30 N", "lat", 35.5),
    ("35°30'S", "lat", -35.5), ("35-30.5N", "lat", 35.508333), ("140-30.5 E", "lon", 140.508333),
    ("170 W", "lon", -170.0), ("-140.25", "lon", -140.25), ("10.5S", "lat", -10.5), ("ND", "lat", np.nan),
])
def test_parse_coord(x, kind, exp):
    got = tabular.parse_coord(x, kind)
    assert (np.isnan(got) and np.isnan(exp)) or got == pytest.approx(exp, abs=1e-5)


@pytest.mark.parametrize("x,exp", [
    (2.5, (2.5, np.nan, False)), ("2.5", (2.5, np.nan, False)), ("<0.3", (0.3, np.nan, True)),
    ("ND", (np.nan, np.nan, True)), ("n.d.", (np.nan, np.nan, True)), ("", (np.nan, np.nan, False)),
    ("1.2±0.3", (1.2, 0.3, False)), ("1.2 +/- 0.3", (1.2, 0.3, False)), ("1,200", (1200.0, np.nan, False)),
    ("abc", (np.nan, np.nan, False)), ("3.1e-2", (0.031, np.nan, False)),
])
def test_parse_value(x, exp):
    v, u, b = tabular.parse_value(x)
    assert (np.isnan(v) and np.isnan(exp[0])) or v == pytest.approx(exp[0])
    assert (np.isnan(u) and np.isnan(exp[1])) or u == pytest.approx(exp[1])
    assert b is exp[2]


@pytest.mark.parametrize("label,exp", [
    ("137Cs", "Cs-137"), ("Cs-137 (Bq/m3)", "Cs-137"), ("cs137", "Cs-137"), ("^137Cs", "Cs-137"), ("Cs_137", "Cs-137"),
    ("90Sr", "Sr-90"), ("Sr-90", "Sr-90"), ("134Cs", "Cs-134"),
    ("239,240Pu", "Pu-239+240"), ("Pu-239+240", "Pu-239+240"), ("239+240Pu (mBq/m3)", "Pu-239+240"), ("Pu239240", "Pu-239+240"),
    ("238Pu", "Pu-238"), ("Pu-239", "Pu-239"), ("240Pu", "Pu-240"), ("241Pu", "Pu-241"),
    ("240Pu/239Pu", "Pu-240/Pu-239"), ("Pu-240/Pu-239 atom ratio", "Pu-240/Pu-239"),
    ("3H", "OTHER:H-3"), ("Tritium (TU)", "OTHER:H-3"), ("241Am", "OTHER:Am-241"),
    ("Latitude", None), ("Depth (m)", None), ("Reference", None),
])
def test_nuclide_from_label(label, exp):
    assert tabular.nuclide_from_label(label) == exp


def test_header_unit():
    assert tabular.header_unit("137Cs (Bq/m3)") == "Bq/m3"
    assert tabular.header_unit("239,240Pu [mBq m-3]") == "mBq m-3"
    assert tabular.header_unit("Depth (m)") is None


# ------------------------------------------------------------------ wide CSV
WIDE_CSV = """Ref No,Cruise,Station,Date,Latitude,Longitude,Depth (m),Region,137Cs (Bq/m3),137Cs error,90Sr (Bq/m3),err,"239,240Pu (mBq/m3)",Pu err,3H (TU)
R1,KH-00-1,St.1,2000-01-15,35.0,140.0,0,North Pacific,2.5,0.3,1.1,0.2,4.0,0.5,0.8
R1,KH-00-1,St.1,2000-01-15,35.0,140.0,500,North Pacific,<0.3,,0.2,0.05,,,
R2,,St.2,1965/06/01,-20.0,-150.0,0,South Pacific,ND,,1.2±0.3,,12,2,
R3,,,19900701,55.0,15.0,0,Baltic,40,4,,,,,
R4,,St.4,2010-03-03,10.0,170.0,100,,,,,,,,
"""


@pytest.fixture
def wide_csv(tmp_path):
    p = tmp_path / "ham_wide.csv"
    p.write_text(WIDE_CSV, encoding="utf-8")
    return p


def test_wide_guess_mapping(wide_csv):
    tables = tabular.load_tables(wide_csv)
    assert len(tables) == 1
    m = tabular.guess_mapping(tables[0][1].columns)
    assert m["format"] == "wide"
    assert m["columns"]["latitude"] == "Latitude" and m["columns"]["date"] == "Date"
    assert m["columns"]["depth_m"] == "Depth (m)" and m["columns"]["source_ref"] == "Ref No"
    nc = m["nuclide_columns"]
    assert nc["137Cs (Bq/m3)"] == {"nuclide": "Cs-137", "unit": "Bq/m3", "unc_column": "137Cs error"}
    assert nc["90Sr (Bq/m3)"]["unc_column"] == "err"
    assert nc["239,240Pu (mBq/m3)"] == {"nuclide": "Pu-239+240", "unit": "mBq/m3", "unc_column": "Pu err"}
    assert nc["3H (TU)"]["nuclide"] == "OTHER:H-3"
    assert m["unmapped_columns"] == []


def test_wide_parse_pacific(wide_csv):
    df, rep = hamglobal.parse(wide_csv)
    schema.validate(df)
    t = rep["tables"][0]
    assert t["format"] == "wide" and t["mapping_used"] == "guessed"
    assert t["dropped_nuclide_counts"] == {"3H (TU)": 1}
    assert rep["n_outside_pacific"] == 1          # Baltic 40 Bq/m3
    assert rep["n_kept"] == 8                     # ND(불검출) 행도 below_dl=True, 값 NaN 으로 유지
    nd = df[(df.nuclide == "Cs-137") & (df.latitude < 0)].iloc[0]
    assert bool(nd["below_dl"]) is True and pd.isna(nd["value_orig"])
    assert (df["source_db"] == "hamglobal2021").all()
    assert df["record_id"].is_unique
    cs = df[(df.nuclide == "Cs-137") & (df.latitude > 0)].sort_values("depth_m")   # R1 정점 두 수심
    assert list(cs["value_orig"]) == [2.5, 0.3] and list(cs["below_dl"]) == [False, True]
    assert cs.iloc[0]["unc_orig"] == 0.3 and cs.iloc[0]["depth_type"] == "surface"
    sr = df[(df.nuclide == "Sr-90") & (df.latitude < 0)].iloc[0]
    assert sr["value_orig"] == 1.2 and sr["unc_orig"] == 0.3        # "1.2±0.3" 셀에서 불확도 추출
    assert sr["sampling_date"] == pd.Timestamp("1965-06-01") and sr["region_orig"] == "South Pacific"
    pu = df[df.nuclide == "Pu-239+240"]
    assert set(pu["unit_orig"]) == {"mBq/m3"} and pu["value_orig"].tolist() == [4.0, 12.0]
    assert (df["date_precision"] == "day").all()
    assert df.iloc[0]["source_ref"] == "R1" and df.iloc[0]["cruise"] == "KH-00-1"
    assert "src_column=137Cs (Bq/m3)" in df.iloc[0]["notes"]


def test_wide_all_regions_keeps_baltic(wide_csv):
    df, rep = hamglobal.parse(wide_csv, pacific_only=False)
    assert rep["n_kept"] == 9 and "n_outside_pacific" not in rep
    assert (df[df.region_orig == "Baltic"]["sampling_date"] == pd.Timestamp("1990-07-01")).all()  # yyyymmdd 정수


# ------------------------------------------------------------------ long XLSX (2 시트, 제목 행 2줄)
LONG_ROWS = [
    # Nuclide, Value, Error, Unit, Year, Month, Day, Lat, Lon, Sampling depth, Reference
    ["Cs-137", 3.0, 0.4, "Bq/m3", 1975, 7, 20, "35 30 N", "140-30.5 E", 0, "Ref A"],
    ["Sr-90", 2.0, 0.3, "Bq/m3", 1975, 7, None, "35 30 N", "140-30.5 E", 0, "Ref A"],
    ["239+240Pu", 5.5, 0.6, "mBq/m3", 1975, None, None, "10.5S", "170 W", 1000, "Ref B"],
    ["H-3", 1.0, 0.1, "TU", 1975, 7, 20, "35 30 N", "140-30.5 E", 0, "Ref A"],
    ["Cs-137", "<0.5", None, "Bq/m3", 2015, 3, 1, 40.0, 150.0, 20, "Ref C"],
]
LONG_COLS = ["Nuclide", "Value", "Error", "Unit", "Year", "Month", "Day", "Lat", "Lon", "Sampling depth", "Reference"]


@pytest.fixture
def long_xlsx(tmp_path):
    p = tmp_path / "ham_long.xlsx"
    with pd.ExcelWriter(p) as xw:
        title = pd.DataFrame([["HAMGlobal2021 test sheet"] + [None] * 10, [None] * 11])
        body = pd.DataFrame(LONG_ROWS, columns=LONG_COLS)
        title.to_excel(xw, sheet_name="Pacific", index=False, header=False)
        body.to_excel(xw, sheet_name="Pacific", index=False, startrow=2)
        body.iloc[:2].to_excel(xw, sheet_name="Other", index=False, startrow=2)
        pd.DataFrame({"note": ["readme only"]}).to_excel(xw, sheet_name="README", index=False)
    return p


def test_long_xlsx_header_detection_and_parse(long_xlsx):
    insp = tabular.inspect_file(long_xlsx)
    names = [t["table"] for t in insp["tables"]]
    assert "Pacific" in names and "Other" in names and "README" not in names   # README 는 열 3개 미만
    pac = next(t for t in insp["tables"] if t["table"] == "Pacific")
    assert pac["columns"][:4] == ["Nuclide", "Value", "Error", "Unit"]
    assert pac["guessed_mapping"]["format"] == "long"
    assert pac["guessed_mapping"]["columns"]["year"] == "Year" and pac["guessed_mapping"]["columns"]["depth_m"] == "Sampling depth"

    df, rep = hamglobal.parse(long_xlsx)
    schema.validate(df)
    assert rep["n_kept"] == 4 + 2                     # Pacific 시트 4 (H-3 제외) + Other 시트 2
    assert {t["table"]: t["dropped_nuclide_counts"] for t in rep["tables"]}["Pacific"] == {"H-3": 1}
    p = df[df.source_file.str.endswith("::Pacific")]
    assert set(p["source_file"]) == {"ham_long.xlsx::Pacific"}
    cs = p[(p.nuclide == "Cs-137") & (p.sampling_date.dt.year == 1975)].iloc[0]
    assert cs["latitude"] == pytest.approx(35.5) and cs["longitude"] == pytest.approx(140.508333, abs=1e-5)
    assert cs["sampling_date"] == pd.Timestamp("1975-07-20") and cs["date_precision"] == "day"
    sr = p[p.nuclide == "Sr-90"].iloc[0]
    assert sr["sampling_date"] == pd.Timestamp("1975-07-01") and sr["date_precision"] == "month"
    pu = p[p.nuclide == "Pu-239+240"].iloc[0]
    assert pu["sampling_date"] == pd.Timestamp("1975-01-01") and pu["date_precision"] == "year"
    assert pu["latitude"] == -10.5 and pu["longitude"] == -170.0 and pu["unit_orig"] == "mBq/m3"
    c2 = p[(p.nuclide == "Cs-137") & (p.sampling_date.dt.year == 2015)].iloc[0]
    assert bool(c2["below_dl"]) is True and c2["value_orig"] == 0.5


# ------------------------------------------------------------------ 매핑 덮어쓰기 / 단위 미상
ODD_CSV = """Konc,Isotope,Breite,Laenge,Datum,Tiefe
2.0,137Cs,35,140,2001-05-05,0
3.0,90Sr,35,140,2001-05-05,10
"""


def test_mapping_override_and_default_unit(tmp_path):
    p = tmp_path / "odd.csv"
    p.write_text(ODD_CSV, encoding="utf-8")
    insp = tabular.inspect_file(p)
    g = insp["tables"][0]["guessed_mapping"]
    assert g["format"] == "unknown" and set(g["unmapped_columns"]) >= {"Konc", "Breite", "Laenge", "Datum", "Tiefe"}
    mapping = {"format": "long", "columns": {"value": "Konc", "nuclide": "Isotope", "latitude": "Breite",
                                              "longitude": "Laenge", "date": "Datum", "depth_m": "Tiefe"}}
    df, rep = hamglobal.parse(p, mapping)
    assert rep["n_kept"] == 2 and rep["n_unit_unknown"] == 2 and (df["unit_orig"] == "UNKNOWN").all()
    df2, rep2 = hamglobal.parse(p, mapping, default_unit="Bq/m3")
    assert rep2["n_unit_unknown"] == 0 and (df2["unit_orig"] == "Bq/m3").all()
    assert rep2["tables"][0]["mapping_used"] == "given"


def test_invalid_rows_dropped_and_reported(wide_csv):
    # R4 행은 농도가 전부 비어 레코드가 생기지 않음. 위도를 지운 사본으로 필수값 결측 검사
    txt = WIDE_CSV.replace("R2,,St.2,1965/06/01,-20.0,-150.0", "R2,,St.2,1965/06/01,,-150.0")
    p = wide_csv.with_name("ham_wide_bad.csv")
    p.write_text(txt, encoding="utf-8")
    df, rep = hamglobal.parse(p, pacific_only=False)
    assert rep["n_dropped_invalid"] == 3 and rep["invalid_reasons"] == {"latitude": 3}
    schema.validate(df)


def test_cli_inspect_and_run(wide_csv, tmp_path, capsys):
    assert hamglobal.main([str(wide_csv), "--inspect"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["tables"][0]["guessed_mapping"]["format"] == "wide"
    mp = tmp_path / "map.json"
    mp.write_text(json.dumps(out["tables"][0]["guessed_mapping"]), encoding="utf-8")
    dest = tmp_path / "out" / "ham"
    assert hamglobal.main([str(wide_csv), "--map", str(mp), "--out", str(dest)]) == 0
    back = pd.read_csv(dest.with_suffix(".csv"))
    assert len(back) == 8 and list(back.columns) == list(schema.COLUMNS)
    assert (tmp_path / "out" / "ham_report.json").exists()
