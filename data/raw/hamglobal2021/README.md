# data/raw/hamglobal2021/ — HAMGlobal2021 원본

**Historical Artificial radioactivity database in Marine environment, Global integrated version 2021**
Aoyama, M. (2021). DOI https://doi.org/10.34355/CRiED.U.Tsukuba.00085 . ERAN Database 페이지 https://eran-database.jp/list/00085.html
163,260 건, 1956–2021, 전 대양. 핵종: ¹³⁴Cs, ¹³⁷Cs, ⁹⁰Sr, ³H (+ ⁸⁹Sr, ²³⁹⁺²⁴⁰Pu, ²⁴¹Am, ¹⁴C). CC BY 4.0 (검색 확인, 접속 후 재확인할 것).

## 아직 모르는 것 (받은 뒤 이 파일에 기록)

- 파일 형식 (xlsx / csv / zip), 시트 구성, 헤더 행 위치
- 열 이름과 단위 표기 방식, 불확도 종류 (1σ/2σ), 검출한계 표기
- 붕괴 보정 여부와 기준일 (채취일 기준값인지, 특정일로 보정된 값인지)
- MARIS 에서 가져온 33,433 건을 구분하는 열이 있는지 (중복 제거에 필요)

## 변환 절차

```bash
# 1) 파일 구조와 자동 추정 매핑 확인
python -m pacific_radio.parsers.hamglobal data/raw/hamglobal2021/<파일> --inspect > data/raw/hamglobal2021/inspect.json
# 2) inspect.json 의 "guessed_mapping" 을 column_map.json 으로 떼어내 실제 열에 맞게 수정
# 3) 변환
python -m pacific_radio.parsers.hamglobal data/raw/hamglobal2021/<파일> --map data/raw/hamglobal2021/column_map.json \
    --default-unit "Bq/m3" --out data/processed/hamglobal2021_pacific_seawater
```
`--default-unit` 은 파일에 단위 정보가 전혀 없을 때만 쓰고, 근거(논문·README 문구)를 아래에 적을 것.

## 입수 기록

| 입수일 | 파일명 | 형식/용량 | 시트 | 비고 |
|---|---|---|---|---|
| | | | | |
