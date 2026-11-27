# 점프부기

점프부기는 장애물을 뛰어넘거나 아래로 달려 통과하는 러너입니다. Python/Pygame **HansungRun Pygame Prototype 1.0**과 HTML/CSS/JavaScript **점프부기 Web 0.1.0**을 함께 보관합니다. 두 버전의 실행과 점수 저장은 독립적입니다. Pygame 기준본은 라즈베리파이 이식과 게임 규칙 참고용으로 유지합니다.

Git 저장소 루트는 이 폴더의 상위입니다. 상위에는 `.github/`, `study/`, 저장소 README가 있고, 현재 `jumpbugi/`에는 게임과 문서를 둡니다. 저장소는 [개인 jumpbugi](https://github.com/gusdnrdl11/jumpbugi)와 [튜터링 jumpbugi](https://github.com/hansung-tutoring/jumpbugi)이며 기존 문서 기준 기본 브랜치는 `main`입니다.

## 실행

아래 명령은 현재 `jumpbugi/` 폴더에서 실행합니다. 기존 확인 환경은 Python 3.13.15·Pygame 2.6.1입니다. 데스크톱 실행에는 Pygame이 필요하고, 웹 로컬 서버는 Python 표준 라이브러리만 사용합니다. 웹 게임 실행에는 Pygame이나 npm 패키지가 필요 없습니다.

```powershell
# Pygame
python -B -m desktop_prototype.main

# 웹: 실행 후 http://127.0.0.1:8000/ 접속
python -B web/serve.py
```

로컬 PostgreSQL 저장을 사용하려면 [백엔드 실행 안내](docs/BACKEND.md)를 따라 가상환경·DB를 준비한 뒤 아래 명령을 실행하고 Chrome과 Edge에서 같은 주소 `http://127.0.0.1:8000/?server=1`을 엽니다. 정적 서버와 API는 기본 포트가 같으므로 동시에 실행할 때는 한쪽 포트를 바꿉니다.

```powershell
./.venv/Scripts/python.exe -B server/local.py run
```

Pygame은 `python -B desktop_prototype/main.py`, `desktop_prototype/` 안에서 `python -B main.py`, 상위 Git 루트에서 `python -B -m jumpbugi.desktop_prototype.main`으로도 실행할 수 있습니다. Windows 웹 실행 래퍼는 `web/start_web.bat`입니다. 휴대폰 접속은 [웹 실행 안내](web/README.md)를 따릅니다.

| 조작 | Pygame | 웹 |
| --- | --- | --- |
| 시작 | 첫 이미지 이후 아무 키 | 인트로 대기에서 시작 버튼·키·터치 |
| 점프 | Space | Space·게임 화면 터치/클릭 |
| 정지·재개 | Esc | 정지: Esc·탭/창 이탈. 재개: Esc·재생 버튼 |
| 재시작 | 게임오버 후 Enter | 게임오버 후 Enter·재시작 버튼 |
| 종료 | 창 닫기·Ctrl+F4 | 브라우저 탭 닫기 |

두 버전 모두 첫 연출 후 플레이하고 재시작은 연출을 생략합니다. Pygame은 480×360, 웹은 640×360 논리 화면입니다. 웹 입력 대기는 인트로 그림을 유지하며 Pygame의 흰 배경 달리기 대기와 다릅니다. 상세한 시작 흐름·계절·장애물·점수·충돌 규칙은 [ARCHITECTURE](docs/ARCHITECTURE.md)에 모았습니다.

웹 닉네임은 시작 대기·게임오버에서 기록판의 **변경** 버튼으로 입력하고 저장·취소합니다. 시작 연출·플레이·일시정지 중에는 변경할 수 없습니다. 편집 중 키 입력은 게임 조작으로 전달하지 않으며 기존 ID·플레이 기록·최고점수를 유지합니다. 서버 모드의 현재 이름·과거 기록 보존과 검증 결과는 [BACKEND](docs/BACKEND.md#2026-11-27-닉네임-입력상태-제한-검증)에 있습니다.

## 프로젝트 지도

```text
jumpbugi/
├── desktop_prototype/     Pygame 소스 11개, 기존 모듈 경계 유지
├── web/                   독립 웹 게임·실행 자산·Node 검사·개발 서버
├── server/                 로컬 FastAPI·PostgreSQL·실행 도구·API 검사
├── docs/
│   ├── ARCHITECTURE.md     현재 구조·실행·데이터 흐름
│   ├── BACKEND.md          로컬 API·DB 실행·스키마·검증·재개 기록
│   ├── CHANGELOG.md        완료 작업·당시 검증 이력
│   ├── TODO.md             미완료 작업
│   ├── GAME_IDEA.md        게임 기획·신규 아이디어
│   ├── STUDY_NOTES.md      Python/Pygame 학습
│   ├── WEB_REVIEW.md       웹 코드 검토·점검 결과·개선 후보
│   ├── WEB_STUDY.md        웹 기술·코드 분석·실습
│   ├── LEARNING_ROADMAP.md 기술별 학습 순서·실습·완료 기준
│   ├── DIFFICULTY_REPORT.json 기존 자동 회피·연속 플레이 보고
│   ├── prompts/           실제 요청 색인·프롬프트 작성 양식
│   └── archive/           과거 설계·검증·배경 생성 프롬프트
├── image/                 Pygame 실행 자산과 보존 이미지
├── txt/                   실제 최고점수와 폴더 안내
├── tests/                 역할별 Python 자동 검사
├── tools/verify_difficulty.py  난이도 검사
├── AGENTS.md               AI 작업·참조 기준
└── README.md               소개·실행·문서 길잡이
```

## 문서와 학습 순서

| 문서 | 관리 목적 |
| --- | --- |
| [ARCHITECTURE](docs/ARCHITECTURE.md) | 디렉터리·주요 함수·호출 관계·데이터 흐름·현재/향후 경계 |
| [BACKEND](docs/BACKEND.md) | 로컬 FastAPI·PostgreSQL 설치·실행·API 계약·저장 검증·재개 지점 |
| [CHANGELOG](docs/CHANGELOG.md) | 실제 완료 작업과 날짜별 검증 기록 |
| [TODO](docs/TODO.md) | 남은 확인·개선·향후 개발 계획 |
| [GAME_IDEA](docs/GAME_IDEA.md) | 날씨·추가 장소·게임 요소 등 미구현 아이디어 |
| [STUDY_NOTES](docs/STUDY_NOTES.md) | Python/Pygame 개념·현재 코드 분석·연습과 해설 |
| [WEB_REVIEW](docs/WEB_REVIEW.md) | 웹 구현 검토·검사 범위와 한계·개선 사항 |
| [WEB_STUDY](docs/WEB_STUDY.md) | HTML/CSS/JavaScript 학습과 코드 읽기·작은 실습 |
| [LEARNING_ROADMAP](docs/LEARNING_ROADMAP.md) | 13개 기술의 선행 지식·학습 순서·독립 실습·완료 기준 |
| [프롬프트 관리](docs/prompts/README.md) | 실제 원문·재사용 양식·기존 설계 자료의 출처와 상태 |
| [웹 README](web/README.md) | 웹 실행·모바일 접속·입력·로컬 기록 안내 |

처음에는 로드맵에서 순서를 정하고 학습 문서를 읽습니다. 구조와 실제 함수를 확인할 때는 ARCHITECTURE와 소스를 대조합니다. 코드 위치는 [Pygame 역할과 연결](docs/ARCHITECTURE.md#pygame-역할과-연결), [웹 이식본 구조](docs/ARCHITECTURE.md#웹-이식본-구조)에서 찾습니다. 웹 학습 관리본은 `docs/WEB_STUDY.md`입니다.

## 검사

```powershell
# jumpbugi/에서 Python 회귀 검사
python -B -m unittest discover -s tests -v

# jumpbugi/web/에서 Node 내장 검사
node --test tests/*.test.js

# jumpbugi/web/에서 설치된 Chrome/Edge의 브라우저 검사
node tools/browser-smoke.mjs http://127.0.0.1:8000/
```

브라우저 검사 전에는 웹 서버를 별도 실행합니다. 검사 환경과 실제 결과는 [CHANGELOG](docs/CHANGELOG.md), 웹 검사의 기존 범위는 [WEB_REVIEW](docs/WEB_REVIEW.md)에 기록합니다. 화면·터치 모사는 실제 휴대폰의 조작감 검증과 구분합니다.

난이도 설정을 바꾼 경우 `jumpbugi/`에서 `python -B tools/verify_difficulty.py --output docs/DIFFICULTY_REPORT.json`으로 재검사합니다. 기존 보고서는 2026-11-22의 25초 슬롯 설정 결과이며 이번 문서 정리 때문에 재생성하지 않습니다. 자동 회피 가능성이 사람의 반응·재미를 입증하지는 않습니다.

## 저장·배포·향후 확장

Pygame 기록은 `desktop_prototype.config.HIGH_SCORE_PATH`가 가리키는 `txt/high_score.txt`입니다. 테스트는 별도 임시 점수 파일을 사용합니다. 기본 웹 모드는 브라우저·접속 주소별 `localStorage`에 결과 최대 50개를 보관하고 상위 5개를 표시하며, 실제 결과가 없으면 예시임을 표시합니다. 선택한 로컬 서버 모드는 신규 결과를 PostgreSQL에 저장하고 사용자별 최고 기록을 함께 표시합니다. 전송 실패 시 브라우저 기록과 최대 50개의 미전송 대기열을 유지합니다.

기록판의 닉네임 옆 **변경** 버튼에서 2~12자의 이름을 선택적으로 설정할 수 있습니다. 바꾸지 않으면 자동 생성 이름으로 바로 플레이합니다. 닉네임을 바꿔도 UUID·기존 결과·최고점수는 유지됩니다. 서버 공동 랭킹은 현재 이름을 표시하고 과거 결과는 당시 이름을 보존합니다. **이 브라우저 최고**와 서버 공동 기록은 저장 범위가 다르므로 점수가 다를 수 있습니다. 과거 로컬 기록을 일괄 업로드하지 않습니다.

웹은 GitHub Pages에 배포되어 있습니다(사용자 제공 운영 상태). [배포 워크플로](../.github/workflows/deploy.yml)는 `./jumpbugi/web`을 업로드합니다. 이번 정리는 워크플로·배포 경로·웹 자산을 유지하며, 원격 실행 이력이나 배포 주소를 새로 검증한 결과는 아닙니다.

[server/](server/README.md)는 로컬 FastAPI·PostgreSQL을 구현합니다. Chrome·Edge 등 브라우저의 UUID는 가명 식별자이며 인증된 계정이 아닙니다. 클라우드 운영과 게임 재연산을 통한 점수 위변조 검증은 향후 범위입니다. GitHub Pages는 기본 브라우저 저장 모드를 유지하며 로컬 DB에 자동 접속하지 않습니다.

## 보존·작업 원칙

[AGENTS.md](AGENTS.md)를 따릅니다. 실행 소스·자산·실제 점수·테스트·도구의 기존 위치와 모듈 경계를 유지합니다. `image/`의 이전 이미지도 배율·위치 기준에 쓰일 수 있어 이름이나 외관만으로 삭제하지 않습니다.

`../study/`, Python 학습 노트, 과거 보관 자료는 현재 구현의 근거와 구분합니다. `study/`의 이전 연습·래퍼는 보존하며 새 독립 실습 공간으로 활용하는 원칙은 로드맵에 정리합니다. 문서 정리를 이유로 게임 소스·실제 점수·학습 코드를 수정하거나 커밋·push하지 않습니다.
