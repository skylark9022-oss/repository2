# 방침 결정 기록 (Decision Log)

결정할 때마다 날짜, 결정 내용, 이유, 영향 범위를 적습니다. 번복하면 지우지 말고 새 항목으로 추가합니다.

## 형식

```
## YYYY-MM-DD  제목
- 결정:
- 이유:
- 영향: (어느 컬럼 / 어느 코드)
- 근거 자료:
```

---

## 2026-10-02  저장소 구조와 원본 보존 원칙
- 결정: 원본은 `data/raw/` 에 그대로 두고 수정하지 않는다. 가공은 전부 코드로 한다. 통합 DB 는 long format 이며 원본 값과 가공 값을 별도 컬럼에 둔다.
- 이유: 단위 환산·붕괴 보정이 잘못됐을 때 원복 가능해야 함 (사용자 요구).
- 영향: `docs/schema.md`, `src/pacific_radio/schema.py`
- 근거 자료: 없음 (설계 결정)

## 2026-10-02  반감기 출처 결정
- 결정: 기본 출처는 DDEP/LNHB 권고값 (`decay.DEFAULT_SOURCE = "DDEP"`). ICRP-107 과 NUBASE2020 값은 교차 검증용으로 `decay.HALF_LIFE_SOURCES` 에 함께 보관.
- 이유: DDEP 는 계측 표준기관(BIPM 산하)의 평가값이고 Cs-137 은 2024 년 재평가(30.018 (22) a)가 반영됨. 세 출처 간 차이는 최대 0.8 % (70 년 보정 기준)로 측정 불확도보다 작음.
- 영향: `src/pacific_radio/decay.py`, `tests/test_decay.py`, `docs/halflife_sources.md`
- 근거 자료: `docs/halflife_sources.md` (출처 URL·검증 등급), `docs/evidence/halflife_in_session_extract.csv`
- 남은 확인: DDEP 값은 검색 발췌로만 확인(🔎). LNHB 표 PDF 를 직접 열어 Pu-241 자릿수와 Cs-137 표 갱신 여부를 확인하면 ✅ 로 승격.

## 2026-10-02  공개 DB 조사 결과 반영
- 결정: 1 차 수집 대상은 MARIS → HAMGlobal2021 → GEOTRACES IDP 순. CTD 결측은 WOD(근처 실측) → WOA23(기후값) 순으로 채움.
- 이유: MARIS 는 1957 년 이후 100 만 건 이상, NetCDF 가 우리 스키마와 같은 long format. HAMGlobal2021 은 태평양 역사 자료(HAM 2004)를 흡수했고 CC BY 4.0. GEOTRACES 는 CTD 짝 자료.
- 영향: `docs/data_sources.md`, `data/external/maris_lut/` (MARIS 코드 해석표)
- 근거 자료: `docs/data_sources.md` 의 등급 표시 참조. 외부 사이트 직접 접속은 차단되어 ✅ 는 PyPI 패키지 기반, 🔎 는 검색 발췌 기반.
- 주의: HAMGlobal2021 에 MARIS 자료 33,433 건이 포함되어 있어 병합 시 중복 제거 규칙이 필요 (미결 항목에 추가).

## 2026-10-02  태평양 범위 판정과 스키마 확장 (MARIS 파서)
- 결정: 태평양 = (경계상자 100°E~290°E, 70°S~66.5°N) OR (MARIS 해역명이 `regions.PACIFIC_AREA_NAMES` 에 포함). 주변 해역(동해·동중국해·남중국해·베링해·산호해 등) 포함.
- 이유: HAM database(2004) 도 태평양과 주변 해역을 함께 다룸. 경계상자만으로는 날짜변경선·해역명 누락을 못 잡고, 해역명만으로는 해역 코드가 없는 파일을 못 거름.
- 영향: `src/pacific_radio/regions.py`, `parsers/maris.py` (`pacific_only=True` 기본)
- 근거 자료: MARIS `dbo_area` 해역명 목록 (`data/external/maris_lut/dbo_area.csv`)
- 한계: 근사 경계. 자바 남쪽 인도양(105~115°E) 이 섞일 수 있음 → 미결 항목 참조.
- 스키마 추가: `region_orig`(출처 해역명), `dl_value_orig`(검출한계값), `date_precision` 에 `unknown`, 핵종에 비율 `Pu-240/Pu-239`, `Pu-238/Pu-239+240`.

## 미결 사항 (결정 필요)
- [ ] 공통 단위: Bq/m³ 로 할지 mBq/kg 로 할지. 질량↔부피 환산 시 밀도 가정 (TEOS-10 으로 현장 밀도 계산 vs 1.025 kg/L 상수) 결정 필요.
- [ ] 붕괴 보정 기준일: 전체를 특정 일자 (예: 2020-01-01) 로 통일할지, 채취일 기준값으로 둘지.
- [x] 반감기 출처: DDEP 로 결정 (위 항목). 남은 일은 LNHB PDF 직접 열람으로 ✅ 승격.
- [ ] MARIS ↔ HAMGlobal2021 중복 제거 규칙 (같은 원문·정점·날짜·수심·값이면 하나로).
- [ ] 태평양 정밀 경계: IHO 해역 경계 shapefile 또는 MARIS 해역 코드만 쓸지. 현재는 근사 경계상자 OR 해역명.
- [ ] 비율 핵종(Pu-240/Pu-239)의 `unit_orig` 표기 통일 (MARIS 는 NOT AVAILABLE 로 옴 → `atom ratio` 로 바꿀지).
- [ ] 경도 표기: -180~180 vs 0~360 (태평양은 날짜변경선 문제).
- [ ] 검출한계 미만 값 처리: 제외 / DL 값 / DL÷2 / DL÷√2.
- [ ] CTD 없는 시료의 기후값 대체: WOA 버전, 기간 (예: 1981–2010 vs decadal), 수심 보간 방법.
