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

## HAMGlobal2021 — `pacific_radio.parsers.hamglobal` (표 형식 공용 엔진 `tabular.py` 사용)

### 전제
HAMGlobal2021 파일의 열 구성은 **확인하지 못했습니다** (`docs/data_sources.md` A3, 🔎 등급). 그래서 열 이름을 고정하지 않고
① 자동 탐지 → ② 사람이 확인·수정하는 매핑 JSON → ③ 변환, 3 단계로 설계했습니다. 실제 파일을 받으면 ①부터 돌리세요.

### 명령줄
```bash
python -m pacific_radio.parsers.hamglobal <파일> --inspect              # 헤더, 첫 5행, 추정 매핑(JSON)
python -m pacific_radio.parsers.hamglobal <파일> --map column_map.json --default-unit Bq/m3 --out data/processed/hamglobal2021_pacific_seawater
# 옵션: --sheet <시트명>  --header-row <n>  --all-regions  --keep-invalid
```
실행 후 "매핑되지 않은 열", "단위를 모르는 행" 경고가 나오면 매핑 JSON 을 고치고 다시 돌립니다.

### 매핑 JSON 구조
```json
{
  "format": "wide",                      // "wide"(핵종별 열) 또는 "long"(핵종 열 + 값 열)
  "columns": {"latitude": "Latitude", "longitude": "Longitude", "date": "Date",
              "year": null, "month": null, "day": null, "depth_m": "Depth (m)",
              "station": "Station", "cruise": "Cruise", "source_ref": "Ref No", "region_orig": "Region",
              "nuclide": null, "value": null, "unc": null, "unit": null, "ref_date": null},
  "nuclide_columns": {"137Cs (Bq/m3)": {"nuclide": "Cs-137", "unit": "Bq/m3", "unc_column": "137Cs error"}},
  "default_unit": null,
  "notes_columns": [],                   // 그대로 notes 에 남길 열
  "sheet": null, "header_row": null
}
```

### 자동 인식 규칙
| 항목 | 인식 |
|---|---|
| 핵종 헤더/셀 | `137Cs`, `Cs-137`, `cs137`, `239,240Pu`, `Pu-239+240`, `240Pu/239Pu` … → 스키마 핵종명. `3H`, `241Am`, `14C`, `89Sr` 은 대상 외로 집계 후 제외 |
| 단위 | 헤더 괄호 `(Bq/m3)`, `[mBq m-3]` → `unit_orig`. 없으면 unit 열 → `--default-unit` → `UNKNOWN` |
| 불확도 열 | `error`, `err`, `unc`, `sd`, `sigma` 가 든 헤더. 핵종이 적혀 있으면 그 핵종에, 아니면 직전 값 열에 연결 |
| 값 셀 | 숫자, `<0.3` (검출한계 미만, 값 = 0.3), `ND`/`n.d.` (미만, 값 NaN), `1.2±0.3` (값+불확도), `1,200` |
| 날짜 | 문자열(여러 형식), 엑셀 일련번호, `yyyymmdd` 정수, 또는 Year/Month/Day 열 (월·일 없으면 1 로 채우고 `date_precision` 에 month/year) |
| 좌표 | 십진수, `35 30 N`, `140-30.5 E`, `35°30'S`, `170 W` |
| 헤더 행 | 상위 20 행 중 문자열 셀이 가장 많은 첫 행 (제목 행이 위에 있어도 됨). `--header-row` 로 지정 가능 |
| 엑셀 | 모든 시트. 열 3 개 미만 시트(README 등)는 건너뜀. `source_file` 은 `파일명::시트명` |

### 검증
`tests/test_tabular_hamglobal.py`: 셀 파서 단위 테스트, wide CSV, 제목 행이 있는 2 시트 long XLSX, 매핑 덮어쓰기, 단위 미상 경고, 명령줄.

## 변환 결과 검증 — `pacific_radio.verify`

파서를 쓰지 않고 원본을 따로 읽어 `data/processed/` 와 대조합니다. 실제 자료를 변환할 때마다 돌리세요.

```bash
# MARIS: NetCDF 를 netCDF4 로 직접 읽어 행마다 위경도·수심·날짜·핵종·값·불확도·단위·검출한계·염분·수온 대조
python -m pacific_radio.verify maris data/raw/maris/123.nc data/processed/maris_pacific_seawater.csv
# 표 형식: source_row 와 notes 의 src_column 으로 원본 셀을 찾아 숫자 셀은 자동 대조, 문자 셀("<0.3", "ND")은 수동 검토 목록
python -m pacific_radio.verify tabular data/raw/hamglobal2021/<파일> data/processed/hamglobal2021_pacific_seawater.csv --map column_map.json
```
종료 코드 0 = 불일치 없음. 결과 JSON 에 `mismatches`(최대 50건), `manual_review`, `missing_source_rows` 가 들어 있습니다.

전체 검증 한 번에 (실제 MARIS 형식 샘플 + 정답을 아는 합성 자료 3,000 정점):
```bash
python scripts/run_verification.py        # docs/evidence/verification_report.json 갱신
```
결과 해설은 `docs/verification_report.md`.
