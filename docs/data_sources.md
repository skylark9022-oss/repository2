# 공개 데이터베이스 목록 (검증 결과)

작성일 2026-10-02. 작성 환경의 네트워크 정책이 외부 웹사이트 직접 접속(curl, 페이지 열기)을 전부 차단하여, 아래 두 경로로만 확인했습니다. 각 항목의 **검증 등급**을 반드시 보고 사용하세요.

| 등급 | 뜻 |
|---|---|
| ✅ 1차 확인 | PyPI(허용 호스트)에서 내려받은 공식 패키지·데이터 파일을 세션 안에서 직접 열어 확인 |
| 🔎 검색 확인 | 웹 검색 엔진이 반환한 해당 페이지의 본문 발췌로 확인. 페이지 자체는 열지 못함 |
| ❌ 미확인 | 어느 경로로도 확인하지 못함 |

> 🔎 등급은 "URL 이 실존하고 발췌 내용이 그렇다"는 수준입니다. 실제 다운로드 절차·파일 형식·약관은 본인이 접속해 확인하고, 아래 표의 "확인 상태" 열을 갱신해 주세요.

---

## A. 핵종 농도 데이터베이스

### A1. IAEA MARIS (Marine Radioactivity Information System) — 1순위

| 항목 | 내용 | 등급 |
|---|---|---|
| 운영 | IAEA Environment Laboratories (모나코) | 🔎 |
| URL | https://maris.iaea.org/ (연락처 MARIS.Contact-Point@iaea.org) | 🔎 |
| 규모 | 100만 건 이상, 1957년부터. 해수·생물·퇴적물·부유물. 60종 이상 핵종 | 🔎 |
| 접근 경로 | ① explore 포털(시각화) ② datasets 페이지(데이터셋별 NetCDF 다운로드) ③ MARIS API | 🔎 (marisco 패키지 README 에도 동일 서술 ✅) |
| 형식 | NetCDF4 (그룹 `seawater`/`biota`/`sediment`), CSV 변환 가능 | ✅ 샘플 파일 직접 열어 확인 |
| 라이선스 | NetCDF 전역 속성 `license`: "any use of the data will contain appropriate acknowledgement of the data source(s) and the IAEA Marine Radioactivity Information System (MARIS)" (출처 표기 의무) | ✅ |
| 공식 도구 | PyPI `marisco` 1.9.7 (Apache-2.0), 저자 Franck Albinet·Niall Murphy. 변환기(handler)에 GEOTRACES, TEPCO, HELCOM, OSPAR, MARIS legacy 포함 | ✅ |

**MARIS NetCDF `seawater` 그룹의 변수 (✅ 직접 확인)**
`id, id_provider, lon, lat, smp_depth, tot_depth, time, station, nuclide, value, unit, unc, dl, filt, sal, temp`
- 한 행 = 한 측정값 (long format). 우리 스키마와 같은 구조라 변환이 쉽습니다.
- `nuclide`, `unit`, `dl`, `filt` 는 정수 코드. 해석표는 `data/external/maris_lut/` 에 저장해 두었습니다 (cs137 = 33, sr90 = 12, pu239_240_tot = 77, Bq/m3 = unit 1, `<` 검출한계 = dl 2 등).
- `time` 은 1970-01-01 기준 초(UTC). `sal`, `temp` 가 있으므로 **CTD 짝 자료가 일부 들어 있습니다** (샘플에서 temp 는 결측이 많음).
- 해역 코드: North Pacific Ocean = 7, South Pacific Ocean = 8, 세부 해역 61~88.

### A2. HAM database (2004, 태평양 한정) — 역사 자료의 원형

| 항목 | 내용 | 등급 |
|---|---|---|
| 논문 | Aoyama M., Hirose K. (2004) "Artificial Radionuclides Database in the Pacific Ocean: HAM Database", *The Scientific World Journal* 4, 200–215. DOI 10.1100/tsw.2004.15. PMC5956374 (무료 전문) | 🔎 |
| 내용 | ⁹⁰Sr 3,972건, ¹³⁷Cs 7,737건, ²³⁹⁺²⁴⁰Pu 2,666건. 1957–1998. 약 90개 문헌·일본 수로부 연보·미발표 자료. 80% 이상이 태평양·동해, 남태평양은 적음 | 🔎 |
| 비고 | 아래 HAMGlobal2021 에 흡수되었으므로, 실제 다운로드는 A3 로 | — |

### A3. HAMGlobal2021 (쓰쿠바대 CRiED) — 1순위

| 항목 | 내용 | 등급 |
|---|---|---|
| DOI | https://doi.org/10.34355/CRiED.U.Tsukuba.00085 (Aoyama, 2021). ERAN Database 페이지 https://eran-database.jp/list/00085.html | 🔎 |
| 내용 | 163,260건. 주 핵종 ¹³⁴Cs, ¹³⁷Cs, ⁹⁰Sr, ³H. 추가로 ⁸⁹Sr, ²³⁹⁺²⁴⁰Pu, ²⁴¹Am, ¹⁴C. 전 대양, 1956–2021. HAMGlobal2019 23,432건 + 신규 7,789건 + MARIS 재포맷 33,433건 포함 | 🔎 |
| 라이선스 | CRiED 데이터 공개 사이트는 CC BY 4.0 (검색 발췌) | 🔎 |
| 관련 논문 | Inomata Y., Aoyama M. (2023) *Earth System Science Data* 15, 1969– . https://essd.copernicus.org/articles/15/1969/2023/ | 🔎 |
| 주의 | MARIS 자료가 일부 포함되어 있으므로 A1 과 합칠 때 **중복 제거**가 필요합니다 | — |
| 파일 형식 | 미확인 | ❌ |

### A4. GEOTRACES Intermediate Data Product (IDP2021 v2, IDP2025) — CTD 짝 자료

| 항목 | 내용 | 등급 |
|---|---|---|
| URL | https://www.geotraces.org/idp2025/ , 배포 https://www.bodc.ac.uk/geotraces/data/idp2025/ | 🔎 |
| 형식 | ASCII, NetCDF, ODV 컬렉션 | 🔎 |
| 라이선스 | CC BY 4.0. 인용: GEOTRACES Intermediate Data Product Group (2025), doi:10.5285/42c92148-8d03-8be6-e063-7086abc09f0c | 🔎 |
| 핵종 열 이름 | IDP2021 이산 시료 CSV 에 `Cs_137_…`, `Pu_239_D…`, `Pu_240…`, `Pu_239_Pu_240…`, `U_236…`, `Np_237…` 열 존재. 단위는 열 이름 뒤 `[uBq/kg]` 식으로 표기 (예: `Cs_137_D_CONC_BOTTLE [uBq/kg]`) | ✅ marisco `handlers/geotraces.py` 의 정규식·주석에서 확인 |
| 장점 | 같은 병에서 수온·염분·핵종을 측정 → `ctd_source = paired` 로 바로 넣을 수 있음 | — |
| 주의 | IDP2025 에서는 `_BOTTLE`, `_FISH` 등 채수 방식 접미사가 통합되어 열 이름이 바뀜 | 🔎 |

### A5. 일본 — 環境放射線データベース (원자력규제청 위탁, 日本分析センター 운영)

| 항목 | 내용 | 등급 |
|---|---|---|
| URL | https://www.envraddb.go.jp/ (구 search.kankyo-hoshano.go.jp 후신). 전문가용 https://www.envraddb.go.jp/special/database/ , API 안내 https://www.envraddb.go.jp/special/database/api/ | 🔎 |
| 내용 | 1957년부터 전국 환경 시료. 해수 중 Cs-134, Cs-137, Sr-90, H-3, I-131 등 검색 가능. 海洋環境放射能総合評価事業(海生研 수행, Pu-239+240 분석 포함) 결과도 여기서 확인 가능 | 🔎 |
| 출력 | 검색 결과 CSV 출력 가능 | 🔎 |

### A6. 일본 — JAEA 環境モニタリングデータベース (EMDB)

| 항목 | 내용 | 등급 |
|---|---|---|
| URL | 해수 등록 자료 목록 https://emdb.jaea.go.jp/emdb/selects/b10601/ | 🔎 |
| 내용 | 후쿠시마 사고 이후 TEPCO·NRA·후쿠시마현 등 다기관 해수 모니터링을 통일 형식으로 집계. CSV 다운로드, 위경도 WGS84 | 🔎 |

### A7. 일본 — 원자력규제청(NRA) 해역 모니터링 원자료 (후쿠시마 근해)

| 항목 | 내용 | 등급 |
|---|---|---|
| 직접 다운로드 URL | `https://radioactivity.nra.go.jp/cont/en/results/sea/coastal_water.csv` , `https://radioactivity.nra.go.jp/cont/en/results/sea/close1F_water.xlsx` | ✅ marisco `handlers/tepco.py` 에 하드코딩된 URL 로 확인 (실제 접속은 못 함) |
| 정점 좌표 | IAEA ORBS 정점표 (GitHub RML-IAEA/iaea.orbs `station_points.csv`) 를 marisco 가 함께 사용 | ✅ 동일 |
| 포털 | https://radioactivity.nra.go.jp/en/results/sea/off-shore 등 | 🔎 |

### A8. 일본 — 海洋生物環境研究所 (海生研, MERI) 위탁 조사 보고서

| 항목 | 내용 | 등급 |
|---|---|---|
| URL | https://www.kaiseiken.or.jp/publish/itaku/itakuseika.html , 사업 설명 https://www.kaiseiken.or.jp/study/study04.html | 🔎 |
| 내용 | 1983년부터 원자력시설 주변 15해역 + 핵연료사이클시설 해역 해수·퇴적물·생물. Pu-239+240 포함. 보고서(PDF) 형태 | 🔎 |

### A9. 한국 — 원자력안전위원회 / KINS

| 항목 | 내용 | 등급 |
|---|---|---|
| 표층 해수 방사능농도 (CSV) | https://www.data.go.kr/data/15123566/fileData.do . 해역별 Cs 최소·최대, H-3 | 🔎 |
| 해양방사능 조사보고서 DB | https://www.data.go.kr/data/3034070/fileData.do → 실제 파일은 https://clean.kins.re.kr/home/environmentRad/report/ReportMarineRadInquiry.do (PDF). Cs-137, H-3, Sr-90, Pu-239+240, Pu-240/Pu-239 원자비 | 🔎 |
| 범위 | 연안~외양 300 km, 78개 정점 | 🔎 |

### A10. 한국 — 해양수산부 해양환경정보포털 (MEIS)

| 항목 | 내용 | 등급 |
|---|---|---|
| URL | https://www.meis.go.kr/ (해양방사능 감시) | 🔎 |
| 내용 | 2015년부터 연안·항만 165개 정점, 해수 Cs-137, H-3 등 최대 7핵종. 지도 조회·다운로드 | 🔎 |

### A11. WHOI "Our Radioactive Ocean" (북미 서안, 후쿠시마 추적)

| 항목 | 내용 | 등급 |
|---|---|---|
| URL | http://www.ourradioactiveocean.org/results.html | 🔎 |
| 내용 | 2014년부터 시민 참여 채수, Cs-134·Cs-137. 약 200개 시료 | 🔎 |

### A12. Pacific Data Hub 의 MARIS 미러

| 항목 | 내용 | 등급 |
|---|---|---|
| URL | https://pacificdata.org/data/dataset/iaea-marine-information-system-maris | 🔎 |
| 비고 | 원본은 A1. 라이선스 미기재 | 🔎 |

---

## B. CTD / 기후값 보조 자료

### B1. World Ocean Atlas 2023 (WOA23) — 기후값 대체용

| 항목 | 내용 | 등급 |
|---|---|---|
| URL | https://www.ncei.noaa.gov/access/world-ocean-atlas-2023/ | 🔎 |
| 수온·염분 | 1°, 0.25° 격자. 기간: 10년 단위(1955–64 … 2015–22) 및 30년 기후 정규값 1971–2000, 1981–2010, 1991–2020. 표준 수심 102층 | 🔎 |
| 문서 | NOAA Atlas NESDIS 89 (수온), 90 (염분). 제품 문서 PDF 는 ODV 사이트에도 미러 | 🔎 |
| 용도 | 핵종 시료에 CTD 가 없을 때 `ctd_source = woa` 로 채움. 어느 기간 격자를 쓸지는 `decisions.md` 미결 항목 | — |

### B2. World Ocean Database (WOD) — 근처 실측 CTD

| 항목 | 내용 | 등급 |
|---|---|---|
| URL | https://www.ncei.noaa.gov/products/world-ocean-database , 검색 WODselect | 🔎 |
| 내용 | 개별 프로파일 원자료. `OSD`(저해상도 CTD 포함) / `CTD`(고해상도, 2 m 미만 간격) 데이터셋. CSV·netCDF 출력 | 🔎 |
| 용도 | 핵종 정점 근처 같은 시기 CTD 를 찾아 `ctd_source = nearby` | — |

---

## C. 권장 수집 순서

1. **MARIS (A1)** 태평양 해역(area 7, 8, 61~88) 해수 전체를 NetCDF 로 받는다. 코드 해석표는 이미 저장소에 있음.
2. **HAMGlobal2021 (A3)** 을 받아 MARIS 와 중복을 제거한다 (같은 논문 출처·같은 정점·같은 날짜·같은 값).
3. **GEOTRACES IDP (A4)** 로 CTD 짝 자료를 확보한다.
4. 후쿠시마 이후 고밀도 자료가 필요하면 **A5~A7** 을 추가한다.
5. 한국 연안이 필요하면 **A9, A10**.
6. CTD 가 없는 행은 **B2 → B1** 순으로 채운다.

## D. 받을 때 함께 기록할 것 (`data/raw/<출처>/README.md`)

- 접속 URL, 접속일, 검색 조건 (해역·기간·핵종·매질 = 해수)
- 파일 형식, 용량, 다운로드 방법 (웹 폼 / API / 논문 부록)
- 라이선스·인용 문구 (A1 은 출처 표기 의무, A3·A4 는 CC BY 4.0)
- 보고 단위, 붕괴 보정 기준일 표기 방식, 불확도 표기(1σ/2σ), 검출한계 미만 표기(`<`, ND, 빈칸)
