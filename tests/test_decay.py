import math

import pandas as pd
import pytest

from pacific_radio import decay


def test_one_half_life_halves_value():
    t_half = decay.HALF_LIFE_YEARS["Cs-137"]
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
