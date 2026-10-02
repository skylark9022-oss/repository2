# 파서 사용법

파서는 `data/raw/<출처>/` 의 원본을 읽어 통합 스키마(`docs/schema.md`)로 바꿉니다. 원본은 건드리지 않습니다.

## 공통

```bash
pip install -r requirements.txt
pip install -e .            # 또는 PYTHONPATH=src
pytest                      # 파서 테스트 포함
```

## MARIS (IAEA) — `pacific_radio.parsers.maris`

### 입력
MARIS datasets 페이지에서 받은 NetCDF4 파일. 구조 (IAEA `marisco` 템플릿으로 확인):
- 그룹 `seawater` 만 읽음 (biota/sediment/suspended_matter 는 무시)
- 코드 열(`nuclide`, `unit`, `dl`, `area`, `filt`, `count_met` …)은 NetCDF enum. 파일 안의 {이름: 코드} 사전으로 해석하고, enum 이 아닌 파일이면 `data/external/maris_lut/*.csv` 로 해석
- `time` 은 1970-01-01 기준 초(UTC)

### 명령줄
```bash
# 태평양 해수만 (기본)
python -m pacific_radio.parsers.maris data/raw/maris/*.nc --out data/processed/maris_pacific_seawater
# 전 해역
python -m pacific_radio.parsers.maris data/raw/maris/*.nc --all-regions --out data/processed/maris_all_seawater
# 필수값 결측 행도 남기기 (스키마 검증 생략)
python -m pacific_radio.parsers.maris ... --keep-invalid
```
출력: `<out>.csv`, `<out>.parquet`(pyarrow 설치 시), `<out>_report.json`(파일별 처리 보고).

### 파이썬
```python
from pacific_radio.parsers import maris
df, report = maris.parse("data/raw/maris/123.nc")             # 태평양만
raw, attrs = maris.read_seawater("data/raw/maris/123.nc")     # 스키마 변환 전 원시 표 (탐색용)
```

### 변환 규칙
| MARIS | 통합 스키마 | 비고 |
|---|---|---|
| `nuclide` (cs137, sr90, pu239_240_tot, pu240_pu239_ratio …) | `nuclide` | `NUCLIDE_MAP` 에 있는 10 종만 유지. 나머지(h3, am241 …)는 버리고 `report["dropped_nuclide_counts"]` 에 집계 |
| `value`, `unit`, `unc` | `value_orig`, `unit_orig`, `unc_orig` | 단위 이름 `Bq per m3` → `Bq/m3`. 불확도 종류는 MARIS 가 명시하지 않아 `unknown` |
| `dl` (Detected value / Detection limit / Not detected / Derived), `dlv` | `below_dl`, `dl_value_orig` | `Detection limit`, `Not detected` → True |
| `time` | `sampling_date` | `date_precision = unknown` |
| `smp_depth` | `depth_m`, `depth_type` | 0 m → `surface`, 그 외 `measured` |
| `area` | `region_orig` | MARIS 해역명 그대로 |
| `sal`, `temp` | `salinity`, `temperature_c`, `ctd_source` | 둘 중 하나라도 있으면 `paired`, 없으면 `none`. 염분 척도는 `unknown` |
| 전역 속성 `title`, `references`, `id` | `source_ref` | 인용용 |
| `filt`, `lab`, `tot_depth`, 원래 핵종·검출 코드 | `notes` | 자유 기록 |

### 태평양 판정 (`pacific_radio.regions`)
다음 둘 중 하나면 태평양으로 간주:
1. 경계상자: 경도 100°E ~ 290°E(=70°W, 0~360 기준), 위도 70°S ~ 66.5°N
2. MARIS 해역명이 `PACIFIC_AREA_NAMES` 에 포함 (North/South Pacific, 동해, 동중국해, 남중국해, 베링해, 산호해 등 41 개)

근사 경계입니다. 인도양 일부(자바 남쪽)가 섞일 수 있으므로 정밀 분석 전에 해역 코드나 IHO 해역 경계로 재확인하세요 (`docs/decisions.md`).

### 검증
`tests/test_maris_parser.py`
- 실제 MARIS 형식 샘플 (`tests/data/maris_sample_helcom_2024.nc`, IAEA marisco 1.9.7 동봉, 발트해 9 행)
- 합성 파일: 날짜변경선 양쪽 경도, 검출한계 미만, 비율 핵종, 대상 외 핵종, 해역 외, 수심 결측
