# IAEA MARIS 조회표 (lookup tables)

출처: IAEA 가 PyPI 에 배포하는 MARIS 공식 데이터 처리 패키지 `marisco` 1.9.7
(`marisco/files/lut/*.xlsx`, 라이선스 Apache-2.0, 저자 Franck Albinet, Niall Murphy).
2026-10-02 에 PyPI 에서 내려받아 CSV 로 변환했습니다. 내용은 수정하지 않았습니다.

| 파일 | 내용 | 파서에서 쓰는 곳 |
|---|---|---|
| `dbo_nuclide.csv` | 핵종 ID ↔ 이름 (`nc_name`: cs137, sr90, pu239_240_tot …). `half_life` 열은 MARIS 내부 표시용 근사값이며 계측 기준값이 아님 | MARIS NetCDF 의 `nuclide` 정수 코드 해석 |
| `dbo_unit.csv` | 단위 ID ↔ 문자열 (1 = Bq/m3, 3 = Bq/kg …) | `unit` 정수 코드 해석 |
| `dbo_detectlimit.csv` | 검출한계 플래그 (1 `=` 검출값, 2 `<` 검출한계, 3 ND, 4 DE 유도값) | `dl` 코드 → `below_dl` |
| `dbo_area.csv` | 해역 ID (7 North Pacific Ocean, 8 South Pacific Ocean, 61~88 Pacific 세부 해역) | 태평양 자료 선별 |
| `dbo_filtered.csv` | 여과 여부 코드 | `filt` |
| `dbo_sampmet.csv`, `dbo_counmet.csv` | 채취법, 계측법 코드 | `method_orig` |
