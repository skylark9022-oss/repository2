# Pacific Radionuclide Database (태평양 인공핵종 농도 DB)

태평양 해수 중 인공 방사성 핵종 (Pu 동위원소, ⁹⁰Sr, ¹³⁷Cs) 농도를 1950년대부터 최신까지
한곳에 모으고, CTD (수온·염분·수심) 자료와 함께 분석하기 위한 저장소입니다.

## 핵심 원칙

1. **원본은 절대 수정하지 않는다.** 내려받은 파일은 `data/raw/` 에 그대로 두고, 손대지 않습니다.
2. **모든 가공은 코드로 한다.** 단위 환산, 붕괴 보정 등은 `src/` 의 파이썬 코드가 수행하고,
   결과는 `data/processed/` 에 씁니다. 잘못되면 코드를 고치고 다시 돌리면 원복됩니다.
3. **원본 값과 가공 값을 같은 행에 나란히 둔다.** 통합 DB 는 `value_orig`/`unit_orig` (보고된 그대로) 와
   `value_bq_m3` (환산값) 를 모두 가집니다. 자세한 건 `docs/schema.md`.
4. **결정은 기록한다.** 단위·붕괴 보정·기후값 대체 같은 방침은 `docs/decisions.md` 에 날짜와 함께 적습니다.

## 폴더 구조

```
repository2/
├── README.md               ← 이 파일
├── requirements.txt        ← 파이썬 패키지 목록
├── .gitignore              ← 깃이 추적하지 않을 파일 목록
├── data/
│   ├── README.md           ← 데이터 폴더 규칙
│   ├── raw/                ← 내려받은 원본 (수정 금지)
│   ├── interim/            ← 파싱만 한 중간 단계 (재생성 가능)
│   ├── processed/          ← 통합 스키마로 정리된 DB
│   └── external/           ← 보조 자료. maris_lut/ 에 MARIS 코드 해석표 포함. 대용량(.nc)은 깃에서 제외
├── docs/
│   ├── git_guide.md        ← 깃 입문 (처음이면 여기부터)
│   ├── data_sources.md     ← 공개 DB 목록 (검증 등급 표시)
│   ├── halflife_sources.md ← 반감기 출처 비교표 (DDEP / ICRP-107 / NUBASE2020)
│   ├── evidence/           ← 세션 안에서 직접 추출한 검증 자료
│   ├── schema.md           ← 통합 DB 컬럼 정의
│   ├── decisions.md        ← 방침 결정 기록
│   └── data_log.md         ← 데이터 입수 일지
├── notebooks/              ← 탐색용 주피터 노트북
├── src/pacific_radio/
│   ├── schema.py           ← 통합 스키마 정의·검증
│   ├── decay.py            ← 출처별 반감기, 붕괴 보정
│   ├── regions.py          ← 태평양 판정 (경계상자 + MARIS 해역명)
│   ├── store.py            ← data/processed/ 읽기·쓰기
│   └── parsers/
│       ├── maris.py        ← IAEA MARIS NetCDF → 통합 스키마
│       ├── tabular.py      ← CSV/XLSX 공용 엔진 (열 자동 탐지 + 매핑 JSON)
│       └── hamglobal.py    ← HAMGlobal2021 (형식 미확인, --inspect 로 시작)
├── tests/                  ← 코드 검증 테스트 (tests/data/ 에 MARIS 형식 샘플)
└── figures/                ← 그림 산출물
```

## 시작하기

```bash
# 1. 가상환경 (권장)
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. 패키지 설치
pip install -r requirements.txt

# 3. 코드 검증 테스트
pytest

# 4. 노트북 실행
jupyter lab
```

## 작업 흐름 (데이터 하나 추가할 때)

1. 원본을 `data/raw/<출처명>/` 에 넣는다.
2. `docs/data_log.md` 에 입수일, URL, 파일명, 라이선스를 적는다.
3. `notebooks/` 에서 파일을 열어 구조를 파악한다.
4. `src/pacific_radio/` 에 그 출처 전용 파서를 만들어 통합 스키마로 변환한다.
5. 변환 결과를 `data/processed/` 에 저장하고 깃에 커밋한다.

## 단계별 계획

- [ ] 1단계: 공개 DB 에서 자료 수집, 원본 보존 (`data/raw/`) — MARIS·HAMGlobal2021 파서 준비됨, 파일만 받으면 됨
- [ ] 2단계: 통합 스키마로 정리 (`data/processed/`) — MARIS 는 `python -m pacific_radio.parsers.maris` 로
- [ ] 3단계: 단위·붕괴 보정 방침 결정 (`docs/decisions.md`)
- [ ] 4단계: (a) 수심별 연직 프로파일
- [ ] 5단계: (b) T-S 다이어그램 위 농도, (c) 핵종비 기원 추적, (d) 수평 분포도
