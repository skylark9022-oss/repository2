"""끝까지 돌렸을 때 값이 정확히 들어오는지: 원본 ↔ 변환 결과 독립 대조.

1. MARIS 실제 형식 샘플(HELCOM 9행): netCDF4 로 따로 읽은 값과 행 단위 전수 대조 + enum 없는 사본으로 LUT 경로 대조
2. 합성 표 자료(정답 1,500 정점): wide CSV / long XLSX 로 렌더링 → 변환 → 정답과 레코드 단위 전수 대조
3. 저장(CSV, parquet) → 재읽기 왕복 보존
4. 보고서 수치 계정 검사
"""
import sys
from pathlib import Path

import netCDF4 as nc
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent))
import synth_tabular as syn  # noqa: E402

from pacific_radio import schema, verify  # noqa: E402
from pacific_radio.parsers import hamglobal, maris  # noqa: E402

HELCOM = Path(__file__).parent / "data" / "maris_sample_helcom_2024.nc"


# ------------------------------------------------------------------ 1. MARIS
def test_maris_helcom_reconciles_row_by_row():
    df, rep = maris.parse(HELCOM, pacific_only=False)
    res = verify.reconcile_maris(HELCOM, df)
    assert res["n_mismatches"] == 0, res["mismatches"]
    assert res["n_compared"] == 9 and res["n_processed_rows"] == res["n_expected_if_all_regions"] == 9
    assert res["missing_source_rows"] == []
    assert verify.accounting_check(rep)["ok"]


def _strip_enums(src: Path, dst: Path) -> None:
    """enum 변수를 평범한 int64 로 바꾼 사본 (LUT 대체 경로 검사용)."""
    with nc.Dataset(src) as a, nc.Dataset(dst, "w") as b:
        b.setncatts({k: a.getncattr(k) for k in a.ncattrs()})
        g = a.groups["seawater"]; h = b.createGroup("seawater")
        h.createDimension("id", len(g.dimensions["id"]))
        for vn, v in g.variables.items():
            typ = np.int64 if isinstance(v.datatype, nc.EnumType) else (str if v.dtype == str else v.dtype)
            w = h.createVariable(vn, typ, v.dimensions)
            w[:] = (np.ma.filled(v[:], -1).astype(np.int64) if isinstance(v.datatype, nc.EnumType) else v[:])


def test_maris_lut_fallback_matches_enum_path(tmp_path):
    plain = tmp_path / "helcom_plain.nc"
    _strip_enums(HELCOM, plain)
    a, _ = maris.parse(HELCOM, pacific_only=False)
    b, _ = maris.parse(plain, pacific_only=False)
    cols = [c for c in schema.COLUMNS if c not in ("record_id", "source_file")]
    pd.testing.assert_frame_equal(a[cols].reset_index(drop=True), b[cols].reset_index(drop=True))
    res = verify.reconcile_maris(plain, b)
    assert res["n_mismatches"] == 0


# ------------------------------------------------------------------ 2. 합성 표 자료 ↔ 정답
@pytest.fixture(scope="module")
def truth():
    return syn.make_truth(1500, seed=42)


def test_wide_csv_matches_truth(truth, tmp_path):
    p = tmp_path / "synthetic_wide.csv"
    syn.render_wide_csv(truth, p)
    df, rep = hamglobal.parse(p, pacific_only=False)
    tdf = syn.truth_records(truth)
    res = syn.compare_to_truth(df, tdf, idx_from_row=lambda r: int(r["source_row"]))
    assert res["n_mismatches"] == 0, res["mismatches"]
    assert res["n_missing"] == 0 and res["n_matched"] == res["n_truth"] == len(df)
    assert rep["n_dropped_invalid"] == 0 and rep["tables"][0]["unmapped_columns"] == []
    assert verify.accounting_check(rep)["ok"]
    # 원본 셀과의 독립 대조 (숫자 셀 자동, 문자 셀은 수동 검토 목록)
    rc = verify.reconcile_tabular(p, df, rep["tables"][0].get("mapping") or None)
    assert rc["n_mismatches"] == 0, rc["mismatches"]


def test_long_xlsx_matches_truth(truth, tmp_path):
    p = tmp_path / "synthetic_long.xlsx"
    syn.render_long_xlsx(truth, p)
    mapping = None
    df, rep = hamglobal.parse(p, mapping, pacific_only=False)
    tdf = syn.truth_records(truth)
    # 시트 내 행 번호 → 정답 idx 는 truth_idx 열로 (notes 에 남기도록 매핑에 notes_columns 지정)
    from pacific_radio.parsers import tabular
    tables = dict(tabular.load_tables(p))
    g = tabular.guess_mapping(tables["Data"].columns)
    g["notes_columns"] = ["truth_idx"]
    df, rep = hamglobal.parse(p, g, pacific_only=False)
    import re
    res = syn.compare_to_truth(df, tdf, idx_from_row=lambda r: int(re.search(r"truth_idx=(\d+)", r["notes"]).group(1)))
    assert res["n_mismatches"] == 0, res["mismatches"]
    assert res["n_missing"] == 0 and res["n_matched"] == res["n_truth"] == len(df)
    assert rep["n_dropped_invalid"] == 0
    t = rep["tables"][0]
    assert t["table"] == "Data" and t["format"] == "long"


def test_pacific_filter_matches_truth_regions(truth, tmp_path):
    p = tmp_path / "synthetic_wide2.csv"
    syn.render_wide_csv(truth, p)
    df_all, _ = hamglobal.parse(p, pacific_only=False)
    df_pac, rep = hamglobal.parse(p, pacific_only=True)
    tdf = syn.truth_records(truth)
    # 정답 기준: 경계상자(독립 구현) OR 해역명 ∈ {North Pacific, South Pacific, Japan Sea}
    lon360 = np.where(tdf.lon < 0, tdf.lon + 360, tdf.lon)
    in_box = (tdf.lat.between(-70, 66.5)) & (lon360 >= 100) & (lon360 < 290)
    expected = int((in_box | tdf.region.isin(["North Pacific", "South Pacific", "Japan Sea"])).sum())
    assert len(df_pac) == expected
    assert rep["n_outside_pacific"] == len(df_all) - expected


# ------------------------------------------------------------------ 3. 저장 왕복
def test_roundtrip_preserves_values(truth, tmp_path):
    p = tmp_path / "synthetic_wide3.csv"
    syn.render_wide_csv(truth, p)
    df, _ = hamglobal.parse(p, pacific_only=False)
    res = verify.roundtrip_check(df, tmp_path / "out" / "rt")
    assert res["ok"], res["mismatch_cells"]
    m, _ = maris.parse(HELCOM, pacific_only=False)
    res2 = verify.roundtrip_check(m, tmp_path / "out" / "rt_maris")
    assert res2["ok"], res2["mismatch_cells"]
