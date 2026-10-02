# 공개 데이터베이스 후보

> **중요**: 아래 목록은 작성자(Claude)가 학습 데이터로 알고 있는 내용이며,
> 이 저장소를 만든 세션에서는 네트워크 정책 때문에 사이트 접속이 차단되어 **실존 여부·URL·수록 범위를 직접 확인하지 못했습니다.**
> 각 항목을 실제로 열어 본 뒤 "확인 상태" 열을 직접 갱신해 주세요.

| 이름 | 운영 기관 (기억) | 수록 내용 (기억) | 확인 상태 |
|---|---|---|---|
| MARiS (Marine Radioactivity Information System) | IAEA | 전 세계 해수·퇴적물·생물 중 핵종 농도. ¹³⁷Cs, ⁹⁰Sr, Pu 포함 | ☐ 미확인 |
| HAM database (Historical Artificial Radionuclides in the Pacific Ocean and its Marginal Seas) | Aoyama & Hirose (일본 기상연구소 계열) | 태평양 ¹³⁷Cs, ⁹⁰Sr, ²³⁹⁺²⁴⁰Pu 역사 자료 (1957~). 논문: Aoyama & Hirose, *The Scientific World Journal* 4 (2004) 200–215 로 기억 | ☐ 미확인 |
| 海洋環境放射能総合評価事業 데이터 | 일본 海洋生物環境研究所 (MERI) | 일본 주변 해역 해수·퇴적물 핵종 (1983~) | ☐ 미확인 |
| 日本の環境放射能と放射線 (환경방사능 DB) | 일본 原子力規制庁 / 日本分析センター | 일본 전국 환경 시료 핵종 농도 | ☐ 미확인 |
| GEOTRACES Intermediate Data Product | GEOTRACES 국제 프로그램 | 미량 원소·동위원소 단면 관측. CTD 와 짝지어진 자료. 인공핵종 수록 여부는 확인 필요 | ☐ 미확인 |
| 후쿠시마 사고 후 해양 모니터링 | 일본 原子力規制庁, 東京電力 등 | 2011 년 이후 일본 근해 ¹³⁴Cs, ¹³⁷Cs 등 | ☐ 미확인 |

## CTD / 기후값 보조 자료

| 이름 | 운영 기관 (기억) | 용도 | 확인 상태 |
|---|---|---|---|
| World Ocean Atlas (WOA) | NOAA NCEI | 수온·염분 기후값 격자. 핵종 자료에 CTD 가 없을 때 대체 | ☐ 미확인 |
| World Ocean Database (WOD) | NOAA NCEI | 개별 프로파일 관측 원자료. 핵종 정점 근처 CTD 를 찾을 때 | ☐ 미확인 |

## 확인할 때 같이 기록할 것

각 출처마다 아래를 `data/raw/<출처>/README.md` 에 적습니다.

- 접속 URL 과 접속일
- 다운로드 방법 (웹 폼 / API / 논문 부록)
- 검색 조건 (해역, 기간, 핵종, 매질=해수)
- 파일 형식, 용량
- 이용 약관 / 인용 요구 사항
- 보고 단위 (Bq/m³, mBq/kg, mBq/L …) 와 붕괴 보정 기준일 표기 방식
- 불확도 표기 방식 (1σ, 2σ, 계수 오차만 …)
- 검출한계 미만 값 표기 방식 (`<0.5`, `ND`, 빈칸 …)
