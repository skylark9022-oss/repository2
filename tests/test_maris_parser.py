"""MARIS 파서 테스트.

fixture 1: IAEA marisco 1.9.7 에 동봉된 HELCOM(발트해) 샘플 NetCDF (Apache-2.0). 실제 MARIS 형식.
fixture 2: 같은 구조로 만든 합성 파일 (태평양·날짜변경선·검출한계·비율 핵종·결측 수심 검사용).
"""
from pathlib import Path

import netCDF4 as nc
import numpy as np
import pandas as pd
import pytest

from pacific_radio import schema
from pacific_radio.parsers import maris
from pacific_radio.regions import in_pacific_bbox, lon_to_360

HELCOM = Path(__file__).parent / "data" / "maris_sample_helcom_2024.nc"


# ------------------------------------------------------------------ 합성 MARIS 파일
NUCLIDE_ENUM = {"NOT AVAILABLE": 0, "h3": 1, "sr90": 12, "cs137": 33, "pu239_240_tot": 77, "pu240_pu239_ratio": 141}
UNIT_ENUM = {"NOT AVAILABLE": 0, "Bq per m3": 1, "Bq per kg": 3}
DL_ENUM = {"Not available": 0, "Detected value": 1, "Detection limit": 2, "Not detected": 3}
AREA_ENUM = {"Not available": 0, "Baltic Sea": 2, "North Pacific Ocean": 7, "Japan Sea": 4307}

ROWS = [
    # lat, lon, depth, time(s), nuclide, value, unit, unc, dl, dlv, sal, temp, area
    (35.0, 140.0, 0.0, 946684800, "cs137", 2.5, "Bq per m3", 0.3, "Detected value", np.nan, 34.1, 18.2, "North Pacific Ocean"),
    (10.0, -170.0, 500.0, 1262304000, "sr90", 0.4, "Bq per m3", np.nan, "Detection limit", 0.4, np.nan, np.nan, "Not available"),
    (-20.0, 200.0, 1000.0, 1262304000, "pu239_240_tot", 0.002, "Bq per kg", 0.0004, "Detected value", np.nan, 34.5, np.nan, "Not available"),
    (40.0, 135.0, 50.0, 1262304000, "pu240_pu239_ratio", 0.18, "NOT AVAILABLE", 0.01, "Detected value", np.nan, np.nan, np.nan, "Japan Sea"),
    (55.0, 15.0, 0.0, 1262304000, "cs137", 40.0, "Bq per m3", 4.0, "Detected value", np.nan, 7.5, 10.0, "Baltic Sea"),
    (30.0, 150.0, 0.0, 1262304000, "h3", 100.0, "Bq per m3", 10.0, "Detected value", np.nan, np.nan, np.nan, "North Pacific Ocean"),
    (30.0, 150.0, np.nan, 1262304000, "cs137", 1.0, "Bq per m3", 0.1, "Detected value", np.nan, np.nan, np.nan, "North Pacific Ocean"),
]


@pytest.fixture
def synthetic_nc(tmp_path):
    p = tmp_path / "synthetic_maris.nc"
    with nc.Dataset(p, "w", format="NETCDF4") as ds:
        ds.title = "Synthetic MARIS test file"
        ds.references = "doi:10.0000/test"
        ds.id = "ZOTERO1"
        t_nuc = ds.createEnumType(np.int64, "nuclide_t", NUCLIDE_ENUM)
        t_unit = ds.createEnumType(np.int64, "unit_t", UNIT_ENUM)
        t_dl = ds.createEnumType(np.int64, "dl_t", DL_ENUM)
        t_area = ds.createEnumType(np.int64, "area_t", AREA_ENUM)
        g = ds.createGroup("seawater")
        g.createDimension("id", len(ROWS))
        mk = lambda name, typ: g.createVariable(name, typ, ("id",))
        v = {}
        v["id"] = mk("id", np.uint64)
        v["id_provider"] = mk("id_provider", str)
        v["lat"] = mk("lat", np.float32); v["lon"] = mk("lon", np.float32)
        v["smp_depth"] = mk("smp_depth", np.float32); v["time"] = mk("time", np.uint64)
        v["nuclide"] = mk("nuclide", t_nuc); v["value"] = mk("value", np.float32)
        v["unit"] = mk("unit", t_unit); v["unc"] = mk("unc", np.float32)
        v["dl"] = mk("dl", t_dl); v["dlv"] = mk("dlv", np.float32)
        v["sal"] = mk("sal", np.float32); v["temp"] = mk("temp", np.float32)
        v["area"] = mk("area", t_area); v["station"] = mk("station", str)
        for i, r in enumerate(ROWS):
            lat, lon, dep, t, nu, val, un, unc, dl, dlv, sal, temp, area = r
            v["id"][i] = i + 1
            v["id_provider"][i] = f"P{i}"
            v["lat"][i] = lat; v["lon"][i] = lon
            if not np.isnan(dep):
                v["smp_depth"][i] = dep
            v["time"][i] = t
            v["nuclide"][i] = NUCLIDE_ENUM[nu]; v["value"][i] = val
            v["unit"][i] = UNIT_ENUM[un]
            if not np.isnan(unc):
                v["unc"][i] = unc
            v["dl"][i] = DL_ENUM[dl]
            if not np.isnan(dlv):
                v["dlv"][i] = dlv
            if not np.isnan(sal):
                v["sal"][i] = sal
            if not np.isnan(temp):
                v["temp"][i] = temp
            v["area"][i] = AREA_ENUM[area]; v["station"][i] = f"ST{i}"
    return p


# ------------------------------------------------------------------ 실제 MARIS 샘플 (HELCOM)
def test_helcom_sample_reads_and_decodes():
    raw, attrs = maris.read_seawater(HELCOM)
    assert len(raw) == 9
    assert set(raw["nuclide"]) <= {"sr90", "cs137", "cs134", "pu239_240_tot"}
    assert (raw["unit"] == "Bq per m3").all()
    assert "license" in attrs and "MARIS" in attrs["license"]
    assert raw["time"].min().year == 1987


def test_helcom_sample_all_regions_validates():
    df, rep = maris.parse(HELCOM, pacific_only=False)
    assert rep["n_kept"] == 9
    assert rep["n_dropped_other_nuclides"] == 0
    assert set(df["nuclide"]) <= {"Sr-90", "Cs-137", "Cs-134", "Pu-239+240"}
    assert (df["unit_orig"] == "Bq/m3").all()
    assert (df["source_db"] == "maris").all()
    assert df["record_id"].is_unique
    schema.validate(df)
    # CTD 짝: 샘플에는 염분이 모두 있음
    assert (df["ctd_source"] == "paired").all()
    assert df["salinity"].notna().all()


def test_helcom_sample_is_outside_pacific():
    df, rep = maris.parse(HELCOM, pacific_only=True)
    assert rep["n_kept"] == 0
    assert rep["n_outside_pacific"] == 9


# ------------------------------------------------------------------ 합성 파일
def test_synthetic_pacific_filter_and_decoding(synthetic_nc):
    df, rep = maris.parse(synthetic_nc)
    # h3 는 대상 외 핵종, Baltic 은 해역 외, 수심 결측 1행은 invalid
    assert rep["n_dropped_other_nuclides"] == 1 and rep["dropped_nuclide_counts"] == {"h3": 1}
    assert rep["n_outside_pacific"] == 1
    assert rep["n_dropped_invalid"] == 1 and rep["invalid_reasons"] == {"depth_m": 1}
    assert rep["n_kept"] == 4
    schema.validate(df)
    by = df.set_index("nuclide")
    assert set(by.index) == {"Cs-137", "Sr-90", "Pu-239+240", "Pu-240/Pu-239"}
    # 검출한계 미만 행
    sr = by.loc["Sr-90"]
    assert bool(sr["below_dl"]) is True and sr["dl_value_orig"] == pytest.approx(0.4)
    assert sr["ctd_source"] == "none" and pd.isna(sr["salinity_scale"])
    # 날짜변경선 서쪽(-170) 과 0~360 표기(200) 모두 태평양으로 판정됨
    assert sr["longitude"] == pytest.approx(-170.0)
    assert by.loc["Pu-239+240", "longitude"] == pytest.approx(200.0)
    assert by.loc["Pu-239+240", "unit_orig"] == "Bq/kg"
    # 해역명, 표층 판정, 시간 해석
    cs = by.loc["Cs-137"]
    assert cs["region_orig"] == "North Pacific Ocean" and cs["depth_type"] == "surface"
    assert cs["sampling_date"] == pd.Timestamp("2000-01-01")
    assert cs["temperature_c"] == pytest.approx(18.2, abs=1e-4) and cs["ctd_source"] == "paired"
    # 비율 핵종은 단위 NOT AVAILABLE 로 들어옴 (후처리에서 atom ratio 등으로 정리)
    assert by.loc["Pu-240/Pu-239", "unit_orig"] == "NOT AVAILABLE"
    assert by.loc["Pu-240/Pu-239", "region_orig"] == "Japan Sea"
    assert "maris_nuclide=cs137" in cs["notes"]
    assert "title=Synthetic MARIS test file" in cs["source_ref"]


def test_synthetic_keep_invalid(synthetic_nc):
    df, rep = maris.parse(synthetic_nc, drop_invalid=False)
    assert rep["n_kept"] == 5
    assert df["depth_m"].isna().sum() == 1


def test_parse_many_concatenates(synthetic_nc):
    df, rep = maris.parse_many([synthetic_nc, HELCOM], pacific_only=False)
    assert rep["n_files"] == 2
    assert rep["n_kept_total"] == 5 + 9
    assert df["record_id"].is_unique


def test_cli_writes_outputs(synthetic_nc, tmp_path, capsys):
    out = tmp_path / "out" / "maris_pacific_seawater"
    rc = maris.main([str(synthetic_nc), "--out", str(out)])
    assert rc == 0
    assert (out.with_suffix(".csv")).exists()
    assert (tmp_path / "out" / "maris_pacific_seawater_report.json").exists()
    back = pd.read_csv(out.with_suffix(".csv"))
    assert len(back) == 4 and list(back.columns) == list(schema.COLUMNS)


# ------------------------------------------------------------------ 해역 판정
def test_lon_to_360_and_bbox():
    assert list(lon_to_360([-170, 170, 200, -70])) == [190, 170, 200, 290]
    m = in_pacific_bbox([35, 35, 0, 80, -75, 10], [140, -170, 0, 150, 150, -60])
    assert list(m) == [True, True, False, False, False, False]
