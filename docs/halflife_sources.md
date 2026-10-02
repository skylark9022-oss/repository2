# 반감기 출처 비교표

작성일 2026-10-02. 용어: **반감기 (half-life, T½)** 는 방사능이 절반이 되는 시간, **붕괴 상수 (decay constant, λ)** 는 λ = ln 2 / T½ 입니다. 괄호 안 숫자는 마지막 자릿수의 표준불확도입니다 (예: 30.018 (22) a = 30.018 ± 0.022 년). `a` 는 년(annum).

## 검증 등급

| 등급 | 뜻 |
|---|---|
| ✅ 1차 확인 | PyPI 패키지에 내장된 핵데이터를 세션 안에서 직접 읽음. 추출본: `docs/evidence/halflife_in_session_extract.csv` |
| 🔎 검색 확인 | 검색 엔진이 반환한 lnhb.fr / bipm.org / sciencedirect 페이지 본문 발췌로 확인. PDF 자체는 열지 못함 |

## 비교표 (단위: 년)

| 핵종 | DDEP / LNHB 권고값 🔎 | ICRP-107 ✅ | NUBASE2020 (mendeleev 1.3.0 isotopes 표) ✅ | MARIS 조회표 ✅ (표시용 근사값) |
|---|---|---|---|---|
| Cs-137 | **30.018 (22)** — 2024 재평가 (Leblond). 구 DDEP 값 30.05 (8) 가 BIPM CCRI 문서에 남아 있음 | 30.1671 | 30.04 (4) | 30.17 |
| Cs-134 | **2.0644 (14)** = 754.0 (5) d | 2.0648 | 2.065 (0.0004) | 2.07 |
| Sr-90 | **28.80 (7)** = 10 522 (27) d | 28.79 | 28.91 (3) | 28.80 |
| Pu-238 | **87.74 (3)** | 87.7 | 87.7 (1) | 86.40 |
| Pu-239 | **24 100 (11)** | 24 110 | 24 110 (30) | 24 120 |
| Pu-240 | **6 561 (7)** | 6 564 | 6 561 (7) | 6 550 |
| Pu-241 | **14.33 (4)** (검색 발췌값. 소수점 자릿수는 원문 PDF 로 확인 필요) | 14.35 | 14.329 (29) | 14.40 |

- "NUBASE2020" 열: `mendeleev` 패키지 안의 값이며, 패키지 내부에 출처 문구를 찾지 못했습니다. 값이 NUBASE2020 (Kondev et al., 2021, *Chinese Physics C* 45) 의 Cs-137 30.04 y, Sr-90 28.91 y 와 일치하는 것은 검색으로 확인했습니다. 따라서 "NUBASE2020 과 일치하는 값"으로 읽어 주세요.
- MARIS 조회표의 `half_life` 는 DB 표시용이며 계측 기준값이 아닙니다. 비교 참고용으로만 둡니다.

## 출처

DDEP (Decay Data Evaluation Project) 는 BIPM 산하 국제 평가 프로젝트이고, 프랑스 LNHB (Laboratoire National Henri Becquerel) 가 표를 관리합니다. 🔎 표시는 검색 발췌로 확인한 것입니다.

| 핵종 | 문서 |
|---|---|
| Cs-137 | Leblond S. (2024) "DDEP re-evaluation of the radioactive decay scheme of 137Cs", *Applied Radiation and Isotopes* (ScienceDirect S0969804324000198) 🔎; LNHB 평가 주석 http://www.lnhb.fr/nuclides/Cs-137_com.pdf 🔎 |
| Cs-134 | LNHB http://www.lnhb.fr/nuclides/Cs-134_com.pdf (2012 평가) 🔎 |
| Sr-90 | LNHB http://www.lnhb.fr/nuclides/Sr-90_tables.pdf , Sr-90_com.pdf (V. Chisté, 2005) 🔎 |
| Pu-238 | LNHB http://www.lnhb.fr/nuclides/Pu-238_tables.pdf , Pu-238_com.pdf (V.P. Chechev, 2009) 🔎 |
| Pu-239 | LNHB http://www.lnhb.fr/nuclides/Pu-239_tables.pdf 🔎 |
| Pu-240 | LNHB http://www.lnhb.fr/nuclides/Pu-240_tables.pdf , Pu-240_com.pdf (V.P. Chechev) 🔎 |
| Pu-241 | LNHB http://www.lnhb.fr/nuclides/Pu-241_tables.pdf 🔎 |
| ICRP-107 | ICRP (2008) *Nuclear Decay Data for Dosimetric Calculations*, ICRP Publication 107, Ann. ICRP 38(3). 패키지 `radioactivedecay` 0.6.1 (데이터셋 `icrp107_ame2020_nubase2020`) 으로 읽음 ✅ |
| NUBASE2020 | Kondev F.G. et al. (2021) *Chinese Physics C* 45, 030001. https://www-nds.iaea.org/amdc/ame2020/NUBASE2020.pdf 🔎 |

## 값 차이가 분석에 미치는 영향

Cs-137 을 70년 붕괴 보정할 때 (1956년 시료를 2026년 기준으로 환산할 때) 잔존 비율:

| T½ 가정 | 잔존 비율 |
|---|---|
| 30.018 (DDEP 2024) | 0.19862 |
| 30.04 (NUBASE2020) | 0.19885 |
| 30.1671 (ICRP-107) | 0.20021 |

최대 차이 약 0.8 % 로, 해수 측정 불확도(보통 5–20 %)보다 훨씬 작습니다. 다만 출처는 하나로 고정하고 기록해야 재현성이 확보됩니다.

## 결정 (`decisions.md` 에도 기록)

- 기본 출처 = **DDEP / LNHB 권고값**. 계측 표준기관의 평가값이고 최신(Cs-137 2024) 재평가를 반영.
- 교차 검증 = ICRP-107 (`radioactivedecay` 로 자동 비교, `tests/test_decay.py`).
- 사용자가 할 일: LNHB 표 PDF 를 직접 열어 위 🔎 값(특히 Pu-241 소수점, Cs-137 표 갱신 여부)을 확인하고 이 문서의 등급을 ✅ 로 올리기.
