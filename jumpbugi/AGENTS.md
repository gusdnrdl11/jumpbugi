# 점프부기 프로젝트를 다루는 AI 안내

## 현재 구현의 근거

- 프로젝트 관련 답변과 수정은 현재 `desktop_prototype/`의 Python 소스, `web/`의 웹 소스, `tests/`, 루트 `README.md`, `docs/ARCHITECTURE.md`를 기준으로 한다. 문서와 코드가 다르면 실제 코드를 확인한다. Pygame의 이미지·실제 점수·테스트·도구는 루트의 `image/`·`txt/`·`tests/`·`tools/` 위치를 유지한다.
- `docs/GAME_IDEA.md`는 게임 기획·아이디어, `docs/TODO.md`는 미완료 작업이다. 두 문서의 제안을 구현된 기능으로 설명하지 않는다. `docs/CHANGELOG.md`는 작업 당시의 기록이다.
- `docs/WEB_REVIEW.md`는 웹 코드 검토와 날짜별 점검 범위, `docs/WEB_STUDY.md`는 웹 학습 관리본, `docs/LEARNING_ROADMAP.md`는 기술 습득 순서·독립 실습·완료 기준이다. 학습 예제와 향후 과제를 현재 게임의 구현으로 간주하지 않는다. 웹 학습 문서의 이전 이름은 과거 변경 기록에서만 유지한다.
- `server/main.py`·`schema.sql`·`local.py`는 로컬 FastAPI·PostgreSQL과 실행 도구다. `web/src/api.js`는 loopback 주소의 `?server=1`에서 브라우저별 기록을 전송한다. 로컬 저장·사용자별 최고 기록·중복 제출 처리는 코드와 검증 기록을 기준으로 설명하되, 클라우드 운영·사용자 인증·게임 재연산을 통한 점수 위변조 검증은 미구현으로 구분한다. `desktop_prototype/backend.py`는 로컬 게임 로직, `web/serve.py`는 독립 정적 개발 서버다. 실행과 재개 기록은 `docs/BACKEND.md`를 따른다.
- 닉네임 변경은 기존 UUID·과거 결과를 유지한다. `players.nickname`은 현재 이름, `runs.nickname`은 플레이 당시 이름이며 공동 랭킹은 현재 이름을 사용한다. 예전 전송 대기열의 이름을 현재 사용자 이름으로 덮어쓰거나 과거 기록을 일괄 변경하지 않는다. 실제 DB 비밀번호·연결정보는 Git 밖의 로컬 설정에 두고 값 자체를 출력·문서화·커밋하지 않는다.
- `docs/prompts/README.md`에서 실제 요청 원문·재사용 양식·기존 설계 자료를 구분한다. 출처나 사용 이력이 확인되지 않은 프롬프트를 과거 사용 기록으로 만들지 않으며 민감정보를 포함하지 않는다. 기존 보관 원문은 색인에서 연결한다.
- Git 루트는 이 폴더의 상위다. GitHub Pages는 상위 `.github/workflows/deploy.yml`의 `./jumpbugi/web`을 업로드한다. 저장소 문서 경로와 배포 파일 경로를 구분하고, 문서 정리 때문에 실행 소스·자산·워크플로를 이동하거나 기존 모듈을 더 나누지 않는다.

## 기본 탐색·참조에서 제외할 자료

사용자가 해당 자료의 학습·검토·정리를 명시적으로 요청한 경우에만 아래 자료를 읽고 인용한다. 일반적인 게임 개발, 오류 수정, 현재 구조 설명에서는 검색 대상에서 제외하고 구현 근거로 사용하지 않는다.

- 저장소 루트의 `study/` (이 프로젝트에서는 `../study/`): `game01.py`~`game08.py` 및 `prototype_game.py` 등 과거 연습 코드·래퍼. 현재 게임의 진입점이나 의존성이 아니다.
- `docs/STUDY_NOTES.md`: 사람을 위한 통합 학습 노트. 예전 `txt/GAME09_STUDY.txt`와 `txt/게임구조_쉬운설명.txt`의 학습 내용도 이 문서에 모았다.
- `docs/archive/`: 과거 설계, 제안, 검증 기록과 이미지 생성 프롬프트. 현재 사양을 나타내지 않는다.
- `image/이미지자료/`, 원본·미리보기 이미지: 참고 자산. 실제 사용 여부는 `desktop_prototype/`의 `config.py`, `frontend.py`, `assets.py`에서 확인한다.

예외: `txt/high_score.txt`는 `desktop_prototype.config.HIGH_SCORE_PATH`가 가리키는 실제 실행 데이터다. 점수 저장 문제를 다룰 때 필요한 범위에서 확인하되 임의 삭제·초기화하지 않는다. 테스트는 임시 점수 파일을 사용한다.

이 안내는 이 프로젝트 작업에서 상위 `study/`를 어떻게 취급하는지도 명시한다. 상위 폴더의 파일은 현재 게임을 고치기 위해 함께 수정할 필요가 없다. 자료 보존은 실행 가능성이나 내용의 정확성을 보증하지 않는다.
