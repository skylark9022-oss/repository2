# data/raw/maris/ — IAEA MARIS 원본

이 폴더에는 https://maris.iaea.org/ 에서 받은 **NetCDF 파일을 그대로** 둡니다. 수정 금지.

## 받는 방법 (사용자가 확인 후 갱신할 것)

MARIS 는 세 경로를 제공합니다 (docs/data_sources.md A1).
1. explore 포털: 지도에서 해역·핵종·기간을 골라 시각화·내보내기
2. datasets 페이지: 데이터셋(문헌 단위, 파일명은 보통 `<ref_id>.nc`) 별 NetCDF 다운로드
3. MARIS API: 프로그램 접근 (문서는 maris.iaea.org 에서 확인)

이 저장소의 파서(`src/pacific_radio/parsers/maris.py`)는 **2 번의 NetCDF** 를 읽습니다.
포털에서 CSV 로 내보낸 파일은 열 구성이 확인되지 않아 아직 지원하지 않습니다. 받으면 파일을 알려 주세요.

## 입수 기록 (파일마다 한 줄)

| 입수일 | 파일명 | MARIS 데이터셋 제목 / ref_id | 검색 조건 | 용량 | 비고 |
|---|---|---|---|---|---|
| | | | | | |

## 라이선스

MARIS NetCDF 전역 속성 `license` 원문:
> Without prejudice to the applicable Terms and Conditions (https://nucleus.iaea.org/Pages/Others/Disclaimer.aspx), I hereby agree that any use of the data will contain appropriate acknowledgement of the data source(s) and the IAEA Marine Radioactivity Information System (MARIS).

즉 **출처 문헌과 MARIS 를 함께 인용**해야 합니다. 각 파일의 `title`, `references`(DOI), `id`(Zotero 키) 전역 속성이 통합 DB 의 `source_ref` 열에 들어갑니다.

## 변환

```bash
python -m pacific_radio.parsers.maris data/raw/maris/*.nc --out data/processed/maris_pacific_seawater
```
결과: `data/processed/maris_pacific_seawater.csv` (+ `.parquet`, `_report.json`)
