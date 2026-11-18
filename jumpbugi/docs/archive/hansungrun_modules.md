# 한성런 기능별 파일 안내

기존처럼 `python prototype_game.py`로 실행한다. 프론트·백은 같은 Python 프로그램에서 실행하며 별도 서버가 필요하지 않다.

| 파일 | 역할 |
| --- | --- |
| `prototype_game.py` | 실행 시작점, `HansungRun`과 `main` 가져오기 |
| `hansungrun/main.py` | 메인: 키 입력·시간 측정·진행·프론트와 백 연결 |
| `hansungrun/frontend.py` | 프론트: 화면·그림·글꼴·배경 혼합·출력 |
| `hansungrun/backend.py` | 백: 좌표·점프·충돌·점수·장애물·낮밤 시간 |
| `hansungrun/config.py` | 공통 수치와 파일 경로 |
| `hansungrun/assets.py` | 이미지 로딩·크기 조절·모션 4분할 |
| `hansungrun/storage.py` | 최고점수 읽기·임시 파일 교체 저장 |
| `hansungrun/__init__.py` | 패키지 표시 |

## 연결과 실행 흐름

`prototype_game → main → 입력 확인 → backend 상태 갱신 → frontend 출력 → 반복`

메인의 `HansungRun`이 `state`와 `view`를 가진다. `state`는 백의 `GameState`, `view`는 프론트의 `GameView`다. 프론트가 로딩한 이미지의 크기만 백에 전달하므로 백은 화면을 열거나 이미지를 읽지 않고 규칙을 계산할 수 있다. 충돌 도구로 `pygame.Rect`는 사용한다.

낮밤 시간과 혼합 비율은 백이 계산하고 실제 이미지를 섞는 작업은 프론트가 한다. 30초 주기·3초 전환·일시정지·재시작 규칙은 유지했다.

## 바꾸고 싶은 기능을 찾는 방법

- 키 조작: `main.py`의 `handle_events()`
- 점프·충돌·득점: `backend.py`의 `update_step()`
- 무작위 장애물: `backend.py`의 `spawn_obstacle()`
- 점수 위치와 출력 순서: `frontend.py`의 `draw()`
- 속도·중력·전환 시간: `config.py`
- 모션 시트 분할: `assets.py`의 `load_run_frames()`
- 최고점수 저장 정책: `storage.py`

## 기존 코드와 달라진 접근 방법

```python
from prototype_game import HansungRun

# pygame.init()을 실행한 뒤 생성한다.
app = HansungRun()
print(app.state.score)       # 이전 app.score
print(app.state.player_y)    # 이전 app.player_y
print(app.view.run_frames)   # 이전 app.run_frames
app.update(1 / 60)
app.draw()
```

설정은 `hansungrun.config`, 이미지 함수는 `hansungrun.assets`에서 가져온다. 속성을 자동으로 전달하는 숨은 기능을 두지 않고 소유자를 명시했다. 기존 자동 검사도 새 구조에 맞게 변경했다.

이미지는 프로젝트 루트의 `image`에서 찾는다. 최고점수는 사용자가 옮겨 둔 `txt/high_score.txt`를 기본 경로로 사용한다. 기존 기록은 초기화하지 않았다.

## 검증

`python -B -m unittest discover -s test -v`

기존 15개 회귀 검사와 화면·이미지 없이 백의 점프·정지·기록을 확인하는 검사 1개를 사용한다. 과거 `txt/test_game09_candidate.txt`는 분리 전 이력 초안이며 현재 검사는 `test/test_game09.py`다.

최종 실행 결과: 16개 모두 통과 (`Ran 16 tests in 9.882s`, `OK`). 화면을 띄우지 않는 SDL dummy 환경에서 점프·충돌·점수·기록·모션·배경 전환을 검증했다. 실제 창에서의 연속 플레이 감각은 별도 수동 확인 대상이다.
