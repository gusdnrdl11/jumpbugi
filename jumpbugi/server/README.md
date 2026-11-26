# 로컬 FastAPI·PostgreSQL 서버

현재 `main.py`의 FastAPI 앱이 정적 웹과 API를 같은 `127.0.0.1:8000` 출처로 제공하고 PostgreSQL에 브라우저 사용자·완료한 플레이 결과를 저장합니다. `/?server=1`로 접속하면 사용자별 최고 기록을 모은 공동 기록판을 표시합니다. 이는 **로컬 개발 구현**이며 클라우드 배포·계정 인증·점수 위변조 검증은 구현하지 않았습니다. GitHub Pages는 기존 정적 게임과 브라우저 로컬 기록 모드를 계속 사용합니다.

웹의 닉네임 설정은 같은 브라우저 UUID의 현재 이름만 바꿉니다. 공동 기록판은 현재 이름을 표시하고, 이미 저장된 결과의 당시 이름·점수·run_id는 유지합니다. 화면의 개인 최고값은 서버 전체 집계와 구분한 브라우저 로컬 기록입니다.

## Windows에서 준비하고 실행

아래 명령은 프로젝트 `jumpbugi/`에서 실행합니다. `.venv`가 이미 있으면 생성 단계를 생략합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r server/requirements.txt
.\.venv\Scripts\python.exe -B server/local.py setup
.\.venv\Scripts\python.exe -B server/local.py run
```

Chrome과 Edge에서 각각 **http://127.0.0.1:8000/?server=1** 을 엽니다. 같은 주소를 사용해야 동일한 서버를 바라봅니다. API 포트를 바꾸려면 `run --port 8001`로 실행하고 접속 주소도 바꿉니다. 브라우저·포트별 localStorage는 독립적입니다.

`setup`은 `local.py`에 고정한 PostgreSQL Windows 실행 파일을 다운로드하고 SHA256을 확인한 뒤 로컬 클러스터·역할·DB·테이블을 준비합니다. 기존 데이터는 초기화하지 않습니다. DB는 `127.0.0.1:55432`, DB 이름은 `jumpbugi_local`, 앱 역할은 `jumpbugi`입니다. 설치 파일·DB 데이터·로그·비공개 설정은 `%LOCALAPPDATA%\JumpBugi`에 보관합니다. 비밀번호는 로컬에서 생성하며 저장소·명령 예제·보고서에 넣지 않습니다. 설정 파일의 내용을 출력하거나 Git에 복사할 필요가 없습니다.

`run`은 관리 중인 DB를 시작하고 연결 정보를 앱 프로세스에 전달한 뒤 Uvicorn을 loopback 주소로 실행합니다. 서버 터미널의 `Ctrl+C`는 API를 종료하며 DB 데이터는 유지됩니다. DB까지 종료하려면 다음 명령을 별도로 실행합니다.

```powershell
.\.venv\Scripts\python.exe -B server/local.py status
.\.venv\Scripts\python.exe -B server/local.py inspect
.\.venv\Scripts\python.exe -B server/local.py stop-db
```

`inspect`는 사용자별 저장 건수를 출력하며 접속 비밀번호를 출력하지 않습니다. `start-db`는 관리 DB만 다시 시작합니다. 이 관리 도구는 Windows용입니다. 다른 PostgreSQL 환경에서 직접 실행할 때의 연결 방식과 작업 중단·재개 절차는 [BACKEND](../docs/BACKEND.md)를 따릅니다.

## API와 저장 규칙

| 요청 | 현재 동작 |
| --- | --- |
| `GET /api/health` | 실제 DB 연결 검사. 사용 가능하면 200, 연결 불가하면 503 |
| `POST /api/players` | UUID·현재 닉네임(2~12자) 등록. 신규 201, 같은 ID는 이름만 갱신 후 200 |
| `POST /api/runs` | 등록된 사용자의 한 판 저장. 신규 201, 같은 run_id와 같은 내용 재시도는 200 |
| `GET /api/runs?player_id=<UUID>&limit=50` | 해당 사용자의 최근 결과. limit은 1~50 |
| `GET /api/leaderboard?limit=5` | 사용자별 최고 결과를 전체 점수순으로 조회. limit은 1~100 |

`RunInput`은 UUID, 문자열 길이, 숫자 타입·유한값·범위, 시간대가 있는 시각과 기기 구분을 검증합니다. 잘못된 입력은 422, 미등록 사용자의 제출은 404, 기존 run_id에 다른 내용을 넣으면 409입니다. 이러한 검사는 형식과 중복을 처리하며 실제 플레이의 진위를 증명하지 않습니다. 브라우저 ID는 가명 식별자이며 인증된 계정이나 실제 사람을 뜻하지 않습니다.

현재 닉네임은 원문의 `Cc/Cf/Cs/Zl/Zp` 문자를 거부하고 앞뒤 공백 정리 후 Unicode 코드 포인트 2~12자로 제한합니다. 표시 가능한 공백·기호·이모지도 허용하며 이름이 같아도 다른 UUID는 다른 사용자입니다. 과거 결과의 `RunInput.nickname`은 기존 1~40자를 유지합니다. 결과 제출·동일 payload 재시도는 현재 이름을 갱신하지 않습니다. 랭킹은 `players.nickname`을 조인하고 `/api/runs`는 과거 결과의 이름을 반환합니다. 기존 DB 스키마와 행을 변환할 필요가 없습니다.

`schema.sql`은 `players`·`runs`, UUID 기본키/외래키, 값 제약과 조회 인덱스를 정의합니다. 한 요청의 연결은 성공 시 커밋하고 오류 시 롤백합니다. `played_at`은 클라이언트가 제공한 시각이고 `received_at`은 DB가 추가한 수신 시각입니다. 초기화 SQL은 기존 데이터를 지우는 마이그레이션이 아닙니다.

웹은 먼저 `PlayerStore.recordRun()`으로 로컬 결과를 보관합니다. 서버 모드에서는 `LocalServerSync`가 같은 run_id를 전송 대기열에 저장한 뒤 사용자 등록 → 결과 제출 → 공동 기록 조회를 수행합니다. 실패하면 로컬 기록을 유지하고 재시도 버튼·다음 접속·온라인 복귀에서 대기열을 다시 처리합니다. 서버에 연결되기 전의 과거 로컬 결과를 일괄 업로드하지 않습니다.

## 검사와 범위

```powershell
# 실제 PostgreSQL을 사용하는 API 통합 검사: 별도 임시 스키마 사용
.\.venv\Scripts\python.exe -B server/local.py test

# 별도 서버 터미널에서 run을 실행한 뒤, 실제 Chrome·Edge 검사
node tools/verify_local_backend.mjs "http://127.0.0.1:8000/?server=1"

# 출력된 성공 보고서 경로를 사용해 실제 DB 행과 대조
.\.venv\Scripts\python.exe -B server/local.py verify-report --report "web/.qa/local-backend/<실행-ID>/report.json"
```

브라우저 검사는 별도 `.qa` 프로필에서 자연 충돌 결과의 서버 저장·ID 분리·재로딩 보존·중복/잘못된 제출 처리를 확인하는 도구입니다. 설치된 실제 Chrome·Edge와 Node가 필요합니다. `verify-report`는 성공한 두 브라우저 보고서의 ID·제출 내용을 DB에서 직접 조회해 확인하고 같은 폴더에 `database-report.json`을 저장합니다. 접속 비밀번호는 보고하지 않습니다. 실행 결과는 [WEB_REVIEW](../docs/WEB_REVIEW.md)와 [CHANGELOG](../docs/CHANGELOG.md)의 해당 날짜·조건으로 판단하며, 도구가 있다는 사실을 검사 통과로 해석하지 않습니다.

2026-11-26 닉네임 변경 검증은 API 14개·Node 45개와 실제 Chrome/Edge·직접 SQL 대조를 통과했습니다. 현재 이름 변경·같은 UUID와 기존 결과 보존·재접속·과거 대기 결과 재시도를 포함하며, 응답 유실 조건은 QA 대기열에 과거 payload를 넣어 모사했습니다. 상세 증거는 [BACKEND](../docs/BACKEND.md#2026-11-26-닉네임-변경-검증)에 있습니다.

API의 값 검증과 DB 저장을 넘어선 플레이 증거 검증·인증/인가·공개 서버 운영·분석 파이프라인은 [TODO](../docs/TODO.md)의 향후 과제입니다. [전체 구조](../docs/ARCHITECTURE.md#로컬-api와-postgresql), [학습 로드맵](../docs/LEARNING_ROADMAP.md), [BACKEND](../docs/BACKEND.md)에서 호출 관계·학습 순서·운영 절차를 확인합니다.
