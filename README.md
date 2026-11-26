# 점프부기 저장소

점프부기는 Python/Pygame 데스크톱 프로토타입과 HTML/CSS/JavaScript 웹 게임으로 구성된 러너 프로젝트입니다. 게임 실행·개발 문서는 [jumpbugi/README.md](jumpbugi/README.md)에서 확인합니다.

## 저장소 지도

```text
저장소 루트/
├── .github/workflows/deploy.yml  GitHub Pages 정적 배포
├── .gitignore                   Python 캐시·개인 편집기 설정 제외
├── README.md                    저장소 안내
├── jumpbugi/                    현재 게임과 프로젝트 문서
│   ├── desktop_prototype/       Python/Pygame 기준본
│   ├── web/                     독립 웹 게임과 실행 자산
│   ├── server/                  로컬 FastAPI·PostgreSQL·실행 도구
│   ├── docs/                    구조·기록·학습·프롬프트
│   ├── image/                   Pygame 자산과 보존 이미지
│   ├── tests/                   Python 자동 검사
│   ├── tools/                   난이도 검사 도구
│   └── txt/                     실제 Pygame 최고점수
└── study/                       개인 학습·독립 실습 공간
```

로컬 저장소 폴더 이름은 환경에 따라 다를 수 있습니다. 이 환경에서는 `pygame/`가 Git 루트이고 그 안의 `jumpbugi/`가 게임 프로젝트입니다. 아래 명령은 Git 루트에서 실행합니다.

```powershell
# Pygame 프로토타입: Pygame이 설치된 Python 필요
python -B -m jumpbugi.desktop_prototype.main

# 웹: Python 표준 라이브러리 정적 서버
python -B jumpbugi/web/serve.py
```

웹은 `http://127.0.0.1:8000/`에 접속합니다. 두 버전의 실행과 점수 저장은 독립적입니다.

## 개발·학습 안내

- [전체 구조와 데이터 흐름](jumpbugi/docs/ARCHITECTURE.md)
- [기술 학습 로드맵](jumpbugi/docs/LEARNING_ROADMAP.md)
- [Python/Pygame 학습](jumpbugi/docs/STUDY_NOTES.md), [웹 학습](jumpbugi/docs/WEB_STUDY.md)
- [미완료 작업](jumpbugi/docs/TODO.md), [변경 이력](jumpbugi/docs/CHANGELOG.md)
- [프롬프트 관리](jumpbugi/docs/prompts/README.md), [AI 작업 지침](jumpbugi/AGENTS.md)
- [로컬 서버 실행](jumpbugi/server/README.md)

`study/`의 기존 단계별 연습 코드와 예전 래퍼는 학습 자료로 보존합니다. 현재 게임의 진입점이나 실행 의존성이 아니며, 보존이 실행 가능성을 뜻하지는 않습니다. 새 연습은 게임 코드·실제 점수와 분리해서 진행합니다.

## 배포와 확장 상태

웹은 GitHub Pages에 배포되어 있습니다(사용자 제공 운영 상태). [배포 워크플로](.github/workflows/deploy.yml)는 `main` push 또는 수동 실행에서 `./jumpbugi/web`을 업로드합니다. 이 정리는 워크플로와 배포 경로를 변경하지 않습니다. 원격 배포 성공 이력·서비스 주소는 이번 로컬 검증에서 확인하지 않았습니다.

로컬 FastAPI·PostgreSQL을 통한 브라우저별 결과 저장·사용자별 최고 기록을 구현했습니다. [로컬 실행·API·DB·검증 안내](jumpbugi/docs/BACKEND.md)를 따라 같은 `http://127.0.0.1:8000/?server=1` 주소를 Chrome과 Edge에서 엽니다. 클라우드 운영·계정 인증·게임 재연산을 통한 점수 검증은 향후 계획입니다. Pages는 기존 브라우저 저장 모드를 유지합니다.
