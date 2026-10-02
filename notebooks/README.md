# notebooks/

탐색용 주피터 노트북을 둡니다. 번호를 붙여 순서를 알 수 있게 합니다.

```
01_explore_<출처명>.ipynb     ← 원본 파일 구조 파악
02_build_database.ipynb       ← 통합 DB 생성 (src 코드 호출)
03_vertical_profiles.ipynb    ← (a) 수심별 프로파일
```

규칙:
- 재사용할 함수는 노트북에 두지 말고 `src/pacific_radio/` 로 옮깁니다.
- 커밋 전에 `Kernel → Restart & Run All` 로 처음부터 끝까지 도는지 확인합니다.
- 출력이 큰 노트북은 커밋 전에 출력을 지우면 (`Edit → Clear All Outputs`) 깃 용량이 줄어듭니다.
