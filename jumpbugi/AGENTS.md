# 점프부기 프로젝트를 다루는 AI 안내

## 현재 구현의 근거

- 프로젝트 관련 답변과 수정은 현재 `desktop_prototype/`의 Python 소스, `web/`의 웹 소스, `tests/`, 루트 `README.md`, `docs/ARCHITECTURE.md`를 기준으로 한다. 문서와 코드가 다르면 실제 코드를 확인한다. Pygame의 이미지·실제 점수·테스트·도구는 루트의 `image/`·`txt/`·`tests/`·`tools/` 위치를 유지한다.
- `docs/GAME_IDEA.md`는 게임 기획·아이디어, `docs/TODO.md`는 미완료 작업이다. 두 문서의 제안을 구현된 기능으로 설명하지 않는다. `docs/CHANGELOG.md`는 작업 당시의 기록이다.

## 기본 탐색·참조에서 제외할 자료

사용자가 해당 자료의 학습·검토·정리를 명시적으로 요청한 경우에만 아래 자료를 읽고 인용한다. 일반적인 게임 개발, 오류 수정, 현재 구조 설명에서는 검색 대상에서 제외하고 구현 근거로 사용하지 않는다.

- 저장소 루트의 `study/` (이 프로젝트에서는 `../study/`): `game01.py`~`game08.py` 및 `prototype_game.py` 등 과거 연습 코드·래퍼. 현재 게임의 진입점이나 의존성이 아니다.
- `docs/STUDY_NOTES.md`: 사람을 위한 통합 학습 노트. 예전 `txt/GAME09_STUDY.txt`와 `txt/게임구조_쉬운설명.txt`의 학습 내용도 이 문서에 모았다.
- `docs/archive/`: 과거 설계, 제안, 검증 기록과 이미지 생성 프롬프트. 현재 사양을 나타내지 않는다.
- `image/이미지자료/`, 원본·미리보기 이미지: 참고 자산. 실제 사용 여부는 `desktop_prototype/`의 `config.py`, `frontend.py`, `assets.py`에서 확인한다.

예외: `txt/high_score.txt`는 `desktop_prototype.config.HIGH_SCORE_PATH`가 가리키는 실제 실행 데이터다. 점수 저장 문제를 다룰 때 필요한 범위에서 확인하되 임의 삭제·초기화하지 않는다. 테스트는 임시 점수 파일을 사용한다.

이 안내는 이 프로젝트 작업에서 상위 `study/`를 어떻게 취급하는지도 명시한다. 상위 폴더의 파일은 현재 게임을 고치기 위해 함께 수정할 필요가 없다. 자료 보존은 실행 가능성이나 내용의 정확성을 보증하지 않는다.
