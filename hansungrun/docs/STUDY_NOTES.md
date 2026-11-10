# 한성런 학습 노트

> 사람을 위한 학습 자료입니다. AI는 일반 프로젝트 대화에서 이 문서를 참조하지 않습니다. 세부 기준은 [AGENTS](../AGENTS.md)를 따릅니다.

상세 입문 설명은 [쉬운 설명 TXT](../txt/게임구조_쉬운설명.txt), 실제 배치는 [ARCHITECTURE](ARCHITECTURE.md)에 있습니다.

## 먼저 기억할 역할

메인은 입력과 순서, 백은 판단과 숫자, 프론트는 그림과 글자를 맡습니다. 예를 들어 백이 score를 10으로 바꾸면 프론트가 SCORE 10을 그립니다.

config는 공통 기준표, assets는 그림 준비, storage는 기록 도구입니다. 프론트와 백 두 파일로도 만들 수 있지만, 성격이 다른 보조 작업을 꺼내면 필요한 코드를 찾기 쉽습니다. 파일 수가 늘면 import와 파일 이동 관리가 어려워지는 단점도 있어 작은 함수마다 파일을 만들 필요는 없습니다.

## 클래스·객체·상태

클래스는 관련 데이터와 행동을 묶은 설계입니다. GameState()로 만든 객체에는 이번 게임의 현재 상황이 들어 있습니다. self.score는 그 객체의 점수, self.jump()는 점프 동작입니다. HansungRun의 state와 view는 각각 상태 담당과 화면 담당입니다.

## Space 입력 따라가기

`handle_events → state.jump → state.update → player_y 변경 → view.draw`

세로 좌표는 아래로 갈수록 커집니다. 음수 속도로 시작하면 위로 올라가고 중력이 아래 방향 속도를 더합니다. 프론트는 계산된 위치에 그림을 놓습니다.

## dt와 FPS

dt는 지난 반복 이후 흐른 초입니다. FPS는 출력 목표 상한, PHYSICS_HZ는 기존 이동 수치를 환산하는 기준입니다. 백은 긴 지연을 제한하고 작은 단계로 계산해 충돌 누락을 줄입니다.

## 무엇을 바꿀 때 어디를 볼까?

| 바꿀 것 | 먼저 볼 곳 |
| --- | --- |
| 입력 키 | main.handle_events |
| 점프 높이 | config의 JUMP_SPEED·GRAVITY |
| 충돌 판단 | backend.update_step |
| 글자색·위치 | frontend.draw |
| 모션 그림 분할 | assets.load_run_frames |
| 기록 파일 형식 | storage |
| 그림·기록 경로 | config |

## 읽는 순서

config → main의 run → handle_events → backend의 jump와 update → frontend의 draw 순서로 봅니다. assets와 storage는 해당 작업이 궁금할 때 읽습니다. 이후 tests에서 코드로 입력을 넣고 결과를 확인하는 방법을 봅니다.

## 이번 정리에서 배운 점

폴더를 옮기면 코드 경로, 테스트 import, 문서 링크와 명령도 함께 바꿉니다. 파일 위치를 기준으로 절대 경로를 계산하면 터미널 위치에 따른 오류를 줄일 수 있습니다. 자동 테스트가 통과해도 외관과 조작감은 직접 확인합니다.
