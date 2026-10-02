"""반감기 상수와 방사성 붕괴 보정.

용어
----
- 반감기 (half-life, T½): 방사능이 절반으로 줄어드는 데 걸리는 시간.
- 붕괴 상수 (decay constant, λ): λ = ln(2) / T½.
- 붕괴 보정 (decay correction): 측정일 t0 의 활동도 A(t0) 를 기준일 t 의 값으로 환산.
      A(t) = A(t0) · exp(-λ · (t - t0))
  t 가 t0 보다 과거이면 값이 커지고 (역보정), 미래이면 작아진다.

반감기 출처
-----------
출처별 값과 검증 등급은 docs/halflife_sources.md 에 있다. 요약:
- "DDEP"   : DDEP/LNHB 권고값. 검색 발췌로 확인 (PDF 직접 열람 못 함). 기본값.
- "ICRP107": ICRP Publication 107. PyPI `radioactivedecay` 0.6.1 로 세션 내 직접 확인.
- "NUBASE2020": `mendeleev` 1.3.0 isotopes 표 값. NUBASE2020 과 일치함을 검색으로 확인.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

# 1 년 = 365.25 일 (율리우스년). 붕괴 보정의 관례.
DAYS_PER_YEAR = 365.25

# (반감기 [년], 표준불확도 [년] 또는 None)
HALF_LIFE_SOURCES: dict[str, dict[str, tuple[float, float | None]]] = {
    # DDEP / LNHB 권고값 (docs/halflife_sources.md 의 🔎 등급)
    "DDEP": {
        "Cs-137": (30.018, 0.022),   # Leblond 2024 재평가
        "Cs-134": (2.0644, 0.0014),  # = 754.0(5) d
        "Sr-90": (28.80, 0.07),      # = 10522(27) d
        "Pu-238": (87.74, 0.03),
        "Pu-239": (24100.0, 11.0),
        "Pu-240": (6561.0, 7.0),
        "Pu-241": (14.33, 0.04),     # 검색 발췌값. 원문 PDF 로 자릿수 확인 필요
    },
    # ICRP-107 (radioactivedecay 0.6.1 에서 직접 추출, 불확도 미제공)
    "ICRP107": {
        "Cs-137": (30.1671, None),
        "Cs-134": (2.0648, None),
        "Sr-90": (28.79, None),
        "Pu-238": (87.7, None),
        "Pu-239": (24110.0, None),
        "Pu-240": (6564.0, None),
        "Pu-241": (14.35, None),
    },
    # mendeleev 1.3.0 isotopes 표 (NUBASE2020 과 일치)
    "NUBASE2020": {
        "Cs-137": (30.04, 0.04),
        "Cs-134": (2.065, 0.0004),
        "Sr-90": (28.91, 0.03),
        "Pu-238": (87.7, 0.1),
        "Pu-239": (24110.0, 30.0),
        "Pu-240": (6561.0, 7.0),
        "Pu-241": (14.329, 0.029),
    },
}

DEFAULT_SOURCE = "DDEP"

# 하위 호환: 기본 출처의 반감기만 담은 평면 dict
HALF_LIFE_YEARS: dict[str, float] = {
    n: v[0] for n, v in HALF_LIFE_SOURCES[DEFAULT_SOURCE].items()
}


def half_life_years(nuclide: str, source: str = DEFAULT_SOURCE) -> float:
    """반감기 [년]. 출처는 HALF_LIFE_SOURCES 의 키."""
    if source not in HALF_LIFE_SOURCES:
        raise ValueError(f"알 수 없는 출처 '{source}'. 가능한 값: {list(HALF_LIFE_SOURCES)}")
    table = HALF_LIFE_SOURCES[source]
    if nuclide not in table:
        raise ValueError(
            f"'{nuclide}' 의 반감기가 출처 '{source}' 에 정의되어 있지 않습니다. "
            "합산 핵종(Pu-239+240)은 단일 반감기가 없어 붕괴 보정하지 않는 것이 관례입니다 "
            "(두 핵종 모두 반감기가 수천 년 이상이라 수십 년 범위에서는 무시 가능)."
        )
    return table[nuclide][0]


def decay_constant_per_year(nuclide: str, source: str = DEFAULT_SOURCE) -> float:
    """λ [1/year]."""
    return math.log(2.0) / half_life_years(nuclide, source)


def correct_to_date(value, nuclide: str, measured_on, reference_on, source: str = DEFAULT_SOURCE):
    """measured_on 기준 활동도 value 를 reference_on 기준으로 환산.

    value, measured_on 은 스칼라 또는 pandas Series 모두 가능. reference_on 은 단일 날짜.
    """
    lam = decay_constant_per_year(nuclide, source)
    t0 = pd.to_datetime(measured_on)
    t1 = pd.to_datetime(reference_on)
    years = (t1 - t0) / pd.Timedelta(days=DAYS_PER_YEAR)
    return value * np.exp(-lam * np.asarray(years, dtype=float))


def compare_sources(nuclide: str) -> pd.DataFrame:
    """출처별 반감기와 기본 출처 대비 상대 차이(%)를 표로."""
    base = half_life_years(nuclide, DEFAULT_SOURCE)
    rows = []
    for src, table in HALF_LIFE_SOURCES.items():
        if nuclide in table:
            t, u = table[nuclide]
            rows.append(dict(source=src, half_life_y=t, unc_y=u, diff_vs_default_pct=(t / base - 1) * 100))
    return pd.DataFrame(rows)
