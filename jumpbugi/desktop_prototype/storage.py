"""최고점수 파일 읽기와 임시 파일 교체 저장."""
from pathlib import Path

def load_high_score(path):
    try:
        value = int(Path(path).read_text(encoding='utf-8').strip())
    except FileNotFoundError:
        return 0  # 최초 실행에는 저장 파일이 없다.
    if value < 0:
        raise ValueError('최고점수는 음수일 수 없습니다.')
    return value


def save_high_score(path, score):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix('.tmp')
    temporary_path.write_text(str(score), encoding='utf-8')
    temporary_path.replace(path)
