"""해역 판정. 태평양 범위는 근사 경계상자이며 docs/decisions.md 참고.

용어
----
- 경계상자 (bounding box): 위도·경도 최소/최대값으로 정의한 직사각형 영역.
- 날짜변경선 (International Date Line): 경도 180°. 태평양은 이를 가로지르므로
  경도를 0~360° 로 바꿔 비교한다 (서경 170° = 190°).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# 태평양 경계상자 (경도는 0~360 기준). 100°E ~ 290°E(=70°W), 70°S ~ 66.5°N.
# 서쪽 100°E 는 말레이 반도, 북쪽 66.5°N 은 베링 해협, 남쪽 70°S 는 남극 연안.
# 주변 해역(동해, 동중국해, 남중국해, 베링해, 산호해 등)을 포함한다.
# 인도양 일부(자바 남쪽 105~115°E) 가 섞일 수 있으므로 정밀 분석 전 해역 코드로 재확인.
PACIFIC_BBOX = dict(lon_min_360=100.0, lon_max_360=290.0, lat_min=-70.0, lat_max=66.5)

# IAEA MARIS dbo_area.displayName 중 태평양 및 그 주변 해역으로 간주하는 이름.
PACIFIC_AREA_NAMES: frozenset[str] = frozenset({
    "North Pacific Ocean", "South Pacific Ocean",
    "Pacific, Northwest", "Pacific, Northeast", "Pacific, Western Central",
    "Pacific, Eastern Central", "Pacific, Southwest", "Pacific, Southeast", "Pacific, Antarctic",
    "South China & Eastern Archipelagic Seas",
    "Philippine Sea", "East China Sea", "Yellow Sea", "Seto Naikai", "Japan Sea",
    "Sea of Okhotsk", "Bering Sea", "Gulf of Alaska",
    "Coastal Waters of Southeast Alaska and British Columbia", "Gulf of California",
    "South China Sea", "Gulf of Thailand", "Singapore Strait", "Jawa Sea", "Selat Makasar",
    "Bali Sea", "Flores Sea", "Sawu Sea", "Timor Sea", "Arafura Sea", "Banda Sea",
    "Teluk Bone", "Ceram Sea", "Halmahera Sea", "Molucca Sea", "Teluk Tomini",
    "Sulu Sea", "Celebes Sea", "Bismarck Sea", "Solomon Sea", "Coral Sea", "Tasman Sea",
    "Bass Strait",
})


def lon_to_360(lon):
    """경도를 0~360 범위로. 입력은 -180~180 또는 0~360 모두 허용."""
    lon = np.asarray(lon, dtype=float)
    return np.where(lon < 0, lon + 360.0, lon)


def in_pacific_bbox(lat, lon) -> np.ndarray:
    """위경도가 태평양 경계상자 안이면 True. NaN 은 False."""
    lat = np.asarray(lat, dtype=float)
    lon360 = lon_to_360(lon)
    b = PACIFIC_BBOX
    return (
        (lat >= b["lat_min"]) & (lat <= b["lat_max"])
        & (lon360 >= b["lon_min_360"]) & (lon360 < b["lon_max_360"])
    )


def is_pacific_area_name(names) -> np.ndarray:
    """MARIS 해역명이 태평양 목록에 있으면 True. 결측은 False."""
    s = pd.Series(names, dtype="object")
    return s.isin(PACIFIC_AREA_NAMES).to_numpy()


def pacific_mask(lat, lon, region_names=None) -> np.ndarray:
    """경계상자 OR 해역명. region_names 가 None 이면 경계상자만."""
    m = in_pacific_bbox(lat, lon)
    if region_names is not None:
        m = m | is_pacific_area_name(region_names)
    return m
