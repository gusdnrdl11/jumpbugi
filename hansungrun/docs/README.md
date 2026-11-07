# 한성런 문서 안내

한성런은 장애물을 점프로 피하는 Pygame 러너입니다. 기준 폴더는 `hansungrun/`입니다.

## 문서 구조

```text
docs/
├─ README.md                실행 안내와 문서 목차
├─ TODO.md                  다음에 할 일
├─ CHANGELOG.md             완료한 작업과 검증 기록
├─ ARCHITECTURE.md          현재 구조와 실행 흐름
├─ STUDY_NOTES.md           핵심 개념과 학습 순서
├─ 게임구조_쉬운설명.txt     비유와 예시를 넣은 상세 설명
└─ archive/                 이전 문서·배경 보고서·프롬프트
```

## 읽는 순서

1. [쉬운 설명](게임구조_쉬운설명.txt): 파일을 나눈 이유를 처음부터 이해하기
2. [ARCHITECTURE](ARCHITECTURE.md): 현재 배치와 참조 관계 확인
3. [STUDY_NOTES](STUDY_NOTES.md): 코드 개념과 공부 순서
4. [TODO](TODO.md): 다음 작업 선택
5. [CHANGELOG](CHANGELOG.md): 완료한 작업과 검증 결과

## 실행과 검사

확인 환경은 Python 3.13.15, pygame 2.6.1입니다. hansungrun 폴더에서 실행합니다.

```powershell
python main.py
python -B -m unittest discover -s tests -v
```

상위 폴더에서는 `python -m hansungrun.main`으로 실행할 수도 있습니다.

Space: 점프 / Esc: 정지·재개 / 게임오버 후 Enter: 재시작 / Ctrl+F4 또는 창 닫기: 종료

## 파일 관리 원칙

문서는 docs, 이미지는 image, 점수와 기존 텍스트는 txt, 자동 검사는 tests에 둡니다. 실제 최고점수인 `txt/high_score.txt`는 보존합니다.

archive는 과거 자료입니다. 오래된 파일명과 사양이 포함되어 있으므로 현재 실행 안내는 이 README와 ARCHITECTURE를 따릅니다. 상위 study 폴더는 예전 단계별 연습 코드라 현재 게임 정리 대상에서 제외했습니다.

완료 작업은 CHANGELOG, 미완료 작업은 TODO, 구조 변경은 ARCHITECTURE, 학습 내용은 STUDY_NOTES에 적습니다. 경로를 바꾸면 쉬운 설명 TXT도 함께 갱신합니다.
