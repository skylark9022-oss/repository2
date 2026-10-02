# 깃(Git) 입문 가이드

깃을 처음 쓰는 분을 위해 이 저장소에서 실제로 쓰게 될 것만 추렸습니다.

## 1. 용어 정의

| 용어 | 영어 | 뜻 |
|---|---|---|
| 저장소 | repository (repo) | 프로젝트 폴더 전체와 그 변경 이력. 이 폴더(`repository2`)가 저장소입니다. |
| 커밋 | commit | "지금 상태를 사진 찍어 이력에 남기기". 되돌릴 수 있는 저장 지점. |
| 스테이징 | staging (`git add`) | 다음 커밋에 넣을 파일을 고르는 단계. |
| 브랜치 | branch | 이력의 갈래. 기본 갈래 이름은 보통 `main`. |
| 원격 | remote (`origin`) | GitHub 에 있는 복사본. `origin` 은 그 별명. |
| 푸시 | push | 내 컴퓨터의 커밋을 GitHub 로 올리기. |
| 풀 | pull | GitHub 의 커밋을 내 컴퓨터로 내려받기. |
| 클론 | clone | GitHub 의 저장소를 내 컴퓨터에 처음 통째로 복사하기. |

## 2. 처음 한 번만 하는 설정

```bash
git config --global user.name  "본인 이름"
git config --global user.email "GitHub 가입 이메일"
```

GitHub 에 있는 저장소를 내 컴퓨터로 가져오기:

```bash
git clone https://github.com/skylark9022-oss/repository2.git
cd repository2
```

## 3. 매일 쓰는 다섯 명령

```bash
git status                 # 1) 무엇이 바뀌었는지 보기
git add <파일 또는 폴더>   # 2) 커밋에 넣을 파일 고르기 (전부: git add .)
git commit -m "메시지"     # 3) 사진 찍기
git push                   # 4) GitHub 로 올리기
git pull                   # 5) GitHub 의 최신을 받기 (다른 곳에서 작업했을 때)
```

커밋 메시지는 "무엇을 왜 바꿨는지" 한 줄로. 예:
- `MARiS 원본 2024-10 다운로드 추가`
- `Cs-137 단위를 Bq/m3 로 환산하는 함수 추가`

## 4. 이 저장소에서의 습관

- **원본 데이터를 넣을 때**: `data/raw/<출처>/` 에 넣고, 같은 폴더에 `README.md` 로 입수 조건을 적고, 함께 커밋합니다.
- **커밋은 작게, 자주.** 하루 작업 끝에 한 번 몰아서 하면 나중에 되돌리기 어렵습니다.
- **푸시는 커밋 후 바로.** 이 세션 같은 클라우드 환경은 꺼지면 사라지므로, 푸시 안 한 커밋은 잃을 수 있습니다.

## 5. 되돌리기

```bash
git log --oneline          # 커밋 이력 보기 (왼쪽 7자리가 커밋 ID)
git diff                   # 아직 커밋 안 한 변경 내용 보기
git checkout -- <파일>     # 커밋 안 한 변경을 버리고 마지막 커밋 상태로
git revert <커밋ID>        # 특정 커밋을 "취소하는 새 커밋" 만들기 (이력은 남음, 안전)
```

`git reset --hard` 는 이력을 지우므로 익숙해지기 전엔 쓰지 않는 것을 권합니다.

## 6. 브랜치 (지금은 몰라도 됨)

이 저장소에는 현재 `claude/bold-galileo-zmukr8` 브랜치에 작업이 올라가 있습니다.
GitHub 웹에서 이 브랜치를 `main` 으로 합치는 것(Pull Request → Merge) 은 나중에 함께 해도 됩니다.
혼자 쓰는 저장소라면 당분간 브랜치 하나로만 작업해도 충분합니다.

## 7. 막혔을 때

- `git status` 를 먼저 봅니다. 대부분 거기에 다음 할 일이 영어로 적혀 있습니다.
- 공식 문서 (한국어 번역 있음): https://git-scm.com/book/ko/v2
