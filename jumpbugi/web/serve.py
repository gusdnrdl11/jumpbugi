"""Serve only this standalone web directory. No Pygame dependency."""
from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

WEB_ROOT = Path(__file__).resolve().parent


class WebHandler(SimpleHTTPRequestHandler):
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        '.js': 'text/javascript; charset=utf-8',
        '.mjs': 'text/javascript; charset=utf-8',
        '.json': 'application/json; charset=utf-8',
        '.svg': 'image/svg+xml',
    }

    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('X-Content-Type-Options', 'nosniff')
        super().end_headers()


def main():
    parser = argparse.ArgumentParser(description='점프부기 웹 로컬 실행')
    parser.add_argument('--host', default='127.0.0.1', help='모바일 연결 시 0.0.0.0 사용')
    parser.add_argument('--port', type=int, default=8000)
    options = parser.parse_args()
    handler = partial(WebHandler, directory=str(WEB_ROOT))
    try:
        server = ThreadingHTTPServer((options.host, options.port), handler)
    except OSError as error:
        parser.exit(1, f'서버를 시작하지 못했습니다: {error}\n다른 포트: python -B serve.py --port 8001\n')
    address = '127.0.0.1' if options.host == '0.0.0.0' else options.host
    print(f'점프부기 Web: http://{address}:{server.server_port}/', flush=True)
    if options.host == '0.0.0.0':
        print('같은 Wi-Fi 휴대폰: http://<PC의 Wi-Fi IPv4 주소>:' + str(server.server_port), flush=True)
    print('종료: Ctrl+C', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
