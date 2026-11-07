# 한성런 현재 구조

## 폴더 지도

```text
hansungrun/
├─ main.py              실행·입력·반복 순서
├─ frontend.py          화면과 UI
├─ backend.py           상태와 게임 규칙
├─ config.py            공통 설정과 내부 경로
├─ assets.py            이미지 준비
├─ storage.py           최고점수 읽기·저장
├─ __init__.py          패키지 표시
├─ docs/
│  ├─ README.md
│  ├─ TODO.md
│  ├─ CHANGELOG.md
│  ├─ ARCHITECTURE.md
│  ├─ STUDY_NOTES.md
│  ├─ 게임구조_쉬운설명.txt
│  └─ archive/          이전 문서·배경 작업 자료
├─ image/               실행 그림·계절 배경·원본·미리보기
├─ txt/
│  ├─ high_score.txt    실제 기록
│  ├─ BACKGROUND_CHANGE_GUIDE.txt
│  ├─ GAME09_STUDY.txt  과거 학습 자료
│  └─ test_game09_candidate.txt  과거 테스트 초안
└─ tests/
   ├─ __init__.py
   ├─ test_game.py      기본 동작 검사
   └─ test_game09.py    상세 회귀 검사
```

`__pycache__`는 파이썬이 만드는 캐시입니다. 현재 게임은 상위 폴더의 image·txt·테스트·실행 래퍼 없이 실행할 수 있습니다.

## 역할과 연결

```text
main → frontend → assets
main → backend → storage
main / frontend / backend / assets → config
tests → 게임 동작 확인
```

메인·프론트·백은 같은 프로그램입니다. 백은 인터넷 서버가 아니라 게임 규칙 담당입니다. `HansungRun`이 화면 담당 `GameView`와 상태 담당 `GameState`를 보유합니다.

메인은 화면을 먼저 만들고 이미지 크기·모션 수·배경 너비를 백에 전달합니다. 백은 그림 대신 필요한 숫자로 위치와 충돌을 계산합니다. 프론트는 백의 상태를 받아 그립니다. 백도 사각형 계산용 pygame.Rect를 사용하지만 화면을 만들거나 이미지를 읽지는 않습니다.

assets는 그림 읽기·크기 조절·2×2 모션 분리를 맡습니다. storage는 파일을 읽고 임시 파일 교체 방식으로 기록합니다. config는 여러 파일이 공유하는 기준표입니다. 보조 작업을 꺼내면 화면 코드와 규칙 코드를 찾고 수정하기 쉽습니다.

## 실행 순서

`main() → pygame 초기화 → HansungRun 생성 → run() → 종료 시 pygame 정리`

run은 경과 시간 확인 → 입력 처리 → 백 갱신 → 화면 출력 순서로 반복합니다. `game_over`는 이번 판의 종료, `running=False`는 실행 반복 자체의 종료입니다. 정지·게임오버 동안 일반 갱신은 멈춥니다.

## 경로 기준

`config.PROJECT_DIR = Path(__file__).resolve().parent`입니다. config.py가 있는 hansungrun 폴더가 기준이며 터미널의 현재 위치와 무관합니다.

- 이미지: `PROJECT_DIR / 'image'`
- 최고점수: `PROJECT_DIR / 'txt' / 'high_score.txt'`
- 프로젝트를 다른 곳으로 옮길 때도 이 폴더들을 함께 옮깁니다.

## 현재 사양과 저장

480×360, 출력 목표 120FPS, 물리 수치 기준 60Hz입니다. 점프 속도 -15, 중력 0.6, 통과 보너스 10점입니다. 장애물은 세 종류 중 무작위이며 상찌 높이는 40입니다. 달리기는 네 프레임, 낮밤 전환은 30초 간격에 3초 혼합입니다.

신기록은 게임오버 또는 종료 요청 시 저장합니다. 기록이 없으면 0으로 시작하지만 숫자가 아닌 내용이나 음수 기록을 자동 복구하지는 않습니다.

## 검사

`python -B -m unittest discover -s tests -v`로 두 테스트 파일을 검사합니다. 테스트는 별도 임시 점수 파일을 사용합니다. 실제 창의 외관과 조작감은 직접 플레이로 확인합니다.

문서 목차는 [README](README.md), 학습 설명은 [STUDY_NOTES](STUDY_NOTES.md), 이전 자료는 [archive](archive/)를 참고합니다.
