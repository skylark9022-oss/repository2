"""반감기 상수와 방사성 붕괴 보정.

용어
----
- 반감기 (half-life, T½): 방사능이 절반으로 줄어드는 데 걸리는 시간.
- 붕괴 상수 (decay constant, λ): λ = ln(2) / T½.
- 붕괴 보정 (decay correction): 측정일의 활동도 A(t0) 를 기준일 t 의 값으로 환산.
      A(t) = A(t0) · exp(-λ · (t - t0))
  t 가 t0 보다 과거이면 값이 커지고 (역보정), 미래이면 작아진다.

!! 주의 !!
아래 HALF_LIFE_YEARS 값은 작성 시점에 작성자(Claude)가 기억하는 값이며,
이 저장소를 만든 세션에서는 외부 사이트 접속이 차단되어 확인하지 못했습니다.
분석에 쓰기 전에 NNDC NuDat (https://www.nndc.bnl.gov/nudat3/) 또는
DDEP (http://www.lnhb.fr/ddep_wg/) 에서 값을 확인하고, docs/decisions.md 에
출처와 확인일을 기록한 뒤 이 주석을 갱신하세요.
"""
from __future__ import annotations

import math
from datetime import date, datetime

import numpy as np
import pandas as pd

# 단위: 년 (year). 확인 상태: 미확인 (위 주석 참고)
HALF_LIFE_YEARS: dict[str, float] = {
    "Cs-137": 30.08,
    "Cs-134": 2.0652,
    "Sr-90": 28.79,
    "Pu-238": 87.7,
    "Pu-239": 24110.0,
    "Pu-240": 6561.0,
    "Pu-241": 14.329,
}

# 1 년 = 365.25 일 (율리우스년). 붕괴 보정의 관례.
DAYS_PER_YEAR = 365.25


def decay_constant_per_year(nuclide: str) -> float:
    """λ [1/year]. 'Pu-239+240' 처럼 합산 핵종은 단일 반감기가 없어 ValueError."""
    if nuclide not in HALF_LIFE_YEARS:
        raise ValueError(
            f"'{nuclide}' 의 반감기가 정의되어 있지 않습니다. "
            "합산 핵종(Pu-239+240)은 붕괴 보정하지 않는 것이 관례입니다 (반감기가 매우 길어 무시 가능)."
        )
    return math.log(2.0) / HALF_LIFE_YEARS[nuclide]


def correct_to_date(value, nuclide: str, measured_on, reference_on):
    """measured_on 기준 활동도 value 를 reference_on 기준으로 환산.

    value, measured_on 은 스칼라 또는 pandas Series 모두 가능.
    reference_on 은 단일 날짜.
    """
    lam = decay_constant_per_year(nuclide)
    t0 = pd.to_datetime(measured_on)
    t1 = pd.to_datetime(reference_on)
    years = (t1 - t0) / pd.Timedelta(days=DAYS_PER_YEAR)
    return value * np.exp(-lam * np.asarray(years, dtype=float))


def _as_date(d) -> date:
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    return pd.to_datetime(d).date()
