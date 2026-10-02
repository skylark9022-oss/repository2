# 통합 DB 스키마 (`data/processed/`)

한 행 = 한 시료의 한 핵종 측정값 (long format). 컬럼 정의의 정본은 `src/pacific_radio/schema.py` 이며, 이 문서는 설명용입니다.

## 설계 원칙

- **추적 가능성**: 모든 행은 어느 파일의 몇 번째 행에서 왔는지 (`source_db`, `source_file`, `source_row`) 를 가집니다.
- **원본 보존**: 보고된 값·단위·기준일을 `*_orig` 컬럼에 그대로 둡니다. 절대 덮어쓰지 않습니다.
- **가공 값 분리**: 환산값 (`value_bq_m3`) 과 보정 기준일 (`decay_ref_date`) 은 별도 컬럼이며, 방침이 정해지기 전엔 비워 둡니다 (`NaN`).

## 컬럼

### A. 추적
| 컬럼 | 형식 | 설명 |
|---|---|---|
| `record_id` | str | 저장소 내부 고유 ID. `<source_db>:<source_file>:<source_row>` |
| `source_db` | str | 출처 DB 약칭 (`maris`, `ham`, …). `data/raw/` 하위 폴더명과 일치 |
| `source_file` | str | 원본 파일명 |
| `source_row` | int | 원본 파일 내 행 번호 (0부터) |
| `source_ref` | str | 원본이 인용하는 논문·보고서 (있으면) |

### B. 시료 위치·시간
| 컬럼 | 형식 | 설명 |
|---|---|---|
| `cruise` | str | 항해·조사명 |
| `station` | str | 정점명 |
| `sample_id` | str | 출처 DB 의 시료 ID |
| `latitude` | float | 십진수 도, 북위 양수 |
| `longitude` | float | 십진수 도, **동경 양수, -180~180**. 태평양은 날짜변경선을 걸치므로 0~360 으로 바꿀지는 `decisions.md` 에서 결정 |
| `sampling_date` | date | 채취일 (ISO 8601, `YYYY-MM-DD`). 일자 모르면 월 1일로 두고 `date_precision` 에 표시 |
| `date_precision` | str | `day` / `month` / `year` |
| `depth_m` | float | 채취 수심 (m). 표층은 0 |
| `depth_type` | str | `measured` / `nominal` / `surface` |

### C. 핵종 측정값 (보고된 그대로)
| 컬럼 | 형식 | 설명 |
|---|---|---|
| `nuclide` | str | 표준 표기: `Cs-137`, `Cs-134`, `Sr-90`, `Pu-238`, `Pu-239`, `Pu-240`, `Pu-239+240`, `Pu-241` |
| `value_orig` | float | 보고된 값 |
| `unit_orig` | str | 보고된 단위 문자열 그대로 (`Bq/m3`, `mBq/kg`, `mBq/L`, `pCi/L`, …) |
| `unc_orig` | float | 보고된 불확도 |
| `unc_type_orig` | str | `1sigma` / `2sigma` / `counting` / `unknown` |
| `below_dl` | bool | 검출한계 미만이면 True. 이때 `value_orig` 는 검출한계값 |
| `ref_date_orig` | date | 출처가 명시한 붕괴 보정 기준일. 없으면 NaN (채취일 기준으로 추정하지 **않음**) |
| `method_orig` | str | 분석법 (알파분광, ICP-MS, …) 보고된 그대로 |

### D. 가공 값 (방침 결정 후 코드로 채움)
| 컬럼 | 형식 | 설명 |
|---|---|---|
| `value_bq_m3` | float | Bq/m³ 로 환산한 값 |
| `unc_bq_m3` | float | 환산한 불확도 (1σ 로 통일 예정) |
| `decay_ref_date` | date | 붕괴 보정 기준일 (전체 통일값) |
| `value_bq_m3_decay` | float | `decay_ref_date` 로 보정한 값 |
| `processing_version` | str | 가공에 쓴 코드 버전 (깃 커밋 ID 앞 7자리) |

### E. CTD / 수괴
| 컬럼 | 형식 | 설명 |
|---|---|---|
| `temperature_c` | float | 현장 수온 (°C) |
| `salinity` | float | 염분 |
| `salinity_scale` | str | `PSS-78` / `TEOS-10_SA` / `unknown` |
| `ctd_source` | str | `paired` (같은 시료) / `nearby` (근처 관측) / `woa` (기후값) / `none` |
| `ctd_note` | str | 근처 관측이면 거리·시간차, 기후값이면 WOA 버전·기간 |

### F. 비고
| 컬럼 | 형식 | 설명 |
|---|---|---|
| `qc_flag` | str | `ok` / `suspect` / `reject`. 처음엔 전부 `ok` |
| `notes` | str | 자유 기록 |

## 왜 long format 인가

핵종마다 열을 두는 wide format (`cs137`, `sr90`, `pu239240` …) 은 핵종이 늘거나 단위가 섞이면 깨집니다.
long format 은 행을 추가하면 끝이고, `pandas.pivot_table` 로 언제든 wide 로 바꿀 수 있습니다.
