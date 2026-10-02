import math

import pandas as pd
import pytest

from pacific_radio import decay


def test_default_source_is_ddep():
    assert decay.DEFAULT_SOURCE == "DDEP"
    assert decay.HALF_LIFE_YEARS["Cs-137"] == 30.018


def test_one_half_life_halves_value():
    t_half = decay.half_life_years("Cs-137")
    t0 = pd.Timestamp("2000-01-01")
    t1 = t0 + pd.Timedelta(days=t_half * decay.DAYS_PER_YEAR)
    out = decay.correct_to_date(100.0, "Cs-137", t0, t1)
    assert math.isclose(float(out), 50.0, rel_tol=1e-9)


def test_back_correction_increases_value():
    out = decay.correct_to_date(100.0, "Sr-90", "2020-01-01", "1990-01-01")
    assert float(out) > 100.0


def test_series_input():
    s = pd.Series([1.0, 2.0])
    dates = pd.Series(pd.to_datetime(["2000-01-01", "2010-01-01"]))
    out = decay.correct_to_date(s, "Cs-137", dates, "2010-01-01")
    assert len(out) == 2
    assert math.isclose(float(out[1]), 2.0)  # 같은 날짜면 변화 없음
    assert float(out[0]) < 1.0


def test_summed_pu_has_no_single_half_life():
    with pytest.raises(ValueError):
        decay.decay_constant_per_year("Pu-239+240")


def test_unknown_source_rejected():
    with pytest.raises(ValueError):
        decay.half_life_years("Cs-137", source="NOPE")


def test_all_sources_cover_same_nuclides():
    keys = [set(t) for t in decay.HALF_LIFE_SOURCES.values()]
    assert all(k == keys[0] for k in keys)


def test_sources_agree_within_one_percent():
    for n in decay.HALF_LIFE_SOURCES["DDEP"]:
        df = decay.compare_sources(n)
        assert df["diff_vs_default_pct"].abs().max() < 1.0, n


def test_icrp107_table_matches_radioactivedecay_package():
    """docs/halflife_sources.md 의 ICRP-107 열이 패키지 내장값과 같은지 교차 검증."""
    rd = pytest.importorskip("radioactivedecay")
    for n, (t, _) in decay.HALF_LIFE_SOURCES["ICRP107"].items():
        assert math.isclose(rd.Nuclide(n).half_life("y"), t, rel_tol=1e-6), n
