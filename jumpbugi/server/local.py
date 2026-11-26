"""Windows local PostgreSQL lifecycle and API launcher; never resets a database."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import secrets
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from psycopg import Error as DatabaseError

PROJECT = Path(__file__).resolve().parent.parent
VERSION = '18.7-2'
ARCHIVE = f'postgresql-{VERSION}-windows-x64-binaries.zip'
URL = f'https://get.enterprisedb.com/postgresql/{ARCHIVE}'
SHA256 = '74f3740a2e7844118857f297c2067d226f8f2b0652de96022ce54bb27cd60a79'
LOCAL = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) / 'JumpBugi'
BIN = LOCAL / f'postgresql-{VERSION}' / 'pgsql/bin'
DATA = LOCAL / 'postgres-data-18'
CONFIG = LOCAL / 'database.json'


def run(arguments, *, env=None, check=True, capture=False):
    return subprocess.run([str(value) for value in arguments], cwd=PROJECT, env=env,
                          check=check, capture_output=capture, text=True,
                          creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))


def configuration():
    if not CONFIG.is_file():
        raise RuntimeError('Local database is not configured. Run setup first.')
    return json.loads(CONFIG.read_text(encoding='utf-8'))


def connection_info(config, *, admin=False):
    from psycopg.conninfo import make_conninfo
    return make_conninfo(host='127.0.0.1', port=config['port'],
                         dbname='postgres' if admin else 'jumpbugi_local',
                         user='jumpbugi_admin' if admin else 'jumpbugi',
                         password=config['admin_password' if admin else 'password'],
                         connect_timeout=5)


def install_binaries():
    LOCAL.mkdir(parents=True, exist_ok=True)
    archive = LOCAL / ARCHIVE
    if not archive.exists():
        partial = archive.with_suffix('.zip.part')
        print(f'Downloading official PostgreSQL {VERSION} binaries...', flush=True)
        request = urllib.request.Request(URL, headers={'User-Agent': 'JumpBugi-local-development'})
        with urllib.request.urlopen(request, timeout=60) as response, partial.open('wb') as destination:
            total, next_update = 0, 16 * 1024 * 1024
            while chunk := response.read(1024 * 1024):
                destination.write(chunk)
                total += len(chunk)
                if total >= next_update:
                    print(f'Downloaded {total // (1024 * 1024)} MiB', flush=True)
                    next_update += 16 * 1024 * 1024
        partial.replace(archive)
    with archive.open('rb') as source:
        digest = hashlib.file_digest(source, 'sha256').hexdigest()
    if digest != SHA256:
        raise RuntimeError('PostgreSQL archive checksum mismatch; nothing extracted or executed.')
    if (BIN / 'initdb.exe').is_file() and (BIN / 'pg_ctl.exe').is_file():
        return
    destination = LOCAL / f'postgresql-{VERSION}'
    print('Verified official SHA256; extracting PostgreSQL runtime.', flush=True)
    with zipfile.ZipFile(archive) as source:
        for entry in source.infolist():
            name = PurePosixPath(entry.filename)
            if name.is_absolute() or '..' in name.parts or '\\' in entry.filename:
                raise RuntimeError('Unsafe path in PostgreSQL archive.')
            if entry.filename.startswith(('pgsql/bin/', 'pgsql/lib/', 'pgsql/share/')):
                source.extract(entry, destination)


def start_database(config):
    executable = BIN / 'pg_ctl.exe'
    status = run([executable, '-D', DATA, 'status'], check=False, capture=True)
    if status.returncode == 0:
        print('Local PostgreSQL is already running.', flush=True)
        return
    run([executable, '-D', DATA, '-l', LOCAL / 'postgres.log',
         '-o', f"-h 127.0.0.1 -p {config['port']}", '-w', 'start'])


def setup():
    import psycopg
    from psycopg import sql
    if sys.platform != 'win32':
        raise RuntimeError('This portable setup is for Windows; use an installed PostgreSQL elsewhere.')
    install_binaries()
    if not CONFIG.exists():
        if DATA.exists() and any(DATA.iterdir()):
            raise RuntimeError('Existing data without matching configuration; refusing to initialize.')
        config = {'port': 55432, 'password': secrets.token_urlsafe(32),
                  'admin_password': secrets.token_urlsafe(32)}
        CONFIG.write_text(json.dumps(config, indent=2) + '\n', encoding='utf-8')
    config = configuration()
    if not (DATA / 'PG_VERSION').exists():
        password_path = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=LOCAL,
                                             suffix='.pw', delete=False) as password_file:
                password_file.write(config['admin_password'])
                password_path = Path(password_file.name)
            run([BIN / 'initdb.exe', '-D', DATA, '-U', 'jumpbugi_admin',
                 '--encoding=UTF8', '--locale=C', '--auth-local=scram-sha-256',
                 '--auth-host=scram-sha-256', f'--pwfile={password_path}'])
        finally:
            if password_path:
                password_path.unlink(missing_ok=True)
    elif (DATA / 'PG_VERSION').read_text().strip() != '18':
        raise RuntimeError('Existing cluster major version is not 18; refusing to alter it.')
    start_database(config)
    with psycopg.connect(connection_info(config, admin=True), autocommit=True) as connection:
        if not connection.execute('SELECT 1 FROM pg_roles WHERE rolname = %s', ('jumpbugi',)).fetchone():
            connection.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {}').format(
                sql.Identifier('jumpbugi'), sql.Literal(config['password'])))
        if not connection.execute('SELECT 1 FROM pg_database WHERE datname = %s', ('jumpbugi_local',)).fetchone():
            connection.execute(sql.SQL('CREATE DATABASE {} OWNER {}').format(
                sql.Identifier('jumpbugi_local'), sql.Identifier('jumpbugi')))
    with psycopg.connect(connection_info(config)) as connection:
        connection.execute((PROJECT / 'server/schema.sql').read_text(encoding='utf-8'))
    print('Local PostgreSQL ready: 127.0.0.1:55432 / jumpbugi_local (application role: jumpbugi).')
    print(f'Data and private configuration: {LOCAL}')
    print('Next: .venv\\Scripts\\python.exe -B server/local.py run')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['setup', 'start-db', 'stop-db', 'status', 'run', 'test', 'inspect', 'verify-report'])
    parser.add_argument('--port', type=int, default=8000, help='API port; database uses its saved local port')
    parser.add_argument('--report', type=Path, help='Successful Chrome/Edge report to cross-check against PostgreSQL')
    args = parser.parse_args()
    if args.command == 'setup':
        setup()
        return
    config = configuration()
    if args.command == 'start-db':
        start_database(config)
    elif args.command == 'stop-db':
        run([BIN / 'pg_ctl.exe', '-D', DATA, '-m', 'fast', '-w', 'stop'])
    elif args.command == 'status':
        result = run([BIN / 'pg_ctl.exe', '-D', DATA, 'status'], check=False)
        sys.exit(result.returncode)
    elif args.command == 'run':
        start_database(config)
        os.environ['DATABASE_URL'] = connection_info(config)
        sys.path.insert(0, str(PROJECT))
        import uvicorn
        print(f'Chrome and Edge: http://127.0.0.1:{args.port}/?server=1', flush=True)
        uvicorn.run('server.main:app', host='127.0.0.1', port=args.port, reload=False)
    elif args.command == 'test':
        start_database(config)
        environment = {**os.environ, 'TEST_DATABASE_URL': connection_info(config), 'PYTHONDONTWRITEBYTECODE': '1'}
        result = run([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'server/tests', '-v'], env=environment, check=False, capture=True)
        sys.stdout.write(result.stdout or '')
        sys.stderr.write(result.stderr or '')
        sys.exit(result.returncode)
    elif args.command == 'verify-report':
        import psycopg
        from psycopg.rows import dict_row
        from uuid import UUID
        if args.report is None:
            parser.error('verify-report requires --report')
        report = json.loads(args.report.read_text(encoding='utf-8'))
        browsers = report.get('browsers', [])
        if not report.get('passed') or {item.get('name') for item in browsers} != {'Chrome', 'Edge'} or len(browsers) != 2:
            raise RuntimeError('A successful report containing both real browsers is required.')
        if len({item['player_id'] for item in browsers}) != 2:
            raise RuntimeError('Browser identities must be distinct.')
        evidence = []
        with psycopg.connect(connection_info(config), row_factory=dict_row) as connection:
            for browser in browsers:
                rows = connection.execute(
                    'SELECT r.run_id::text, r.player_id::text, r.nickname, r.score, r.survival_time, '
                    'r.game_version, r.device_type, r.death_obstacle, r.max_speed, r.received_at, '
                    'p.nickname AS current_nickname '
                    'FROM runs r JOIN players p ON p.player_id = r.player_id '
                    'WHERE r.run_id = %s AND r.player_id = %s',
                    (UUID(browser['run_id']), UUID(browser['player_id'])),
                ).fetchall()
                expected = browser['submitted_run']
                if len(rows) != 1 or any(rows[0][key] != expected[key] for key in expected if key != 'played_at'):
                    raise RuntimeError('Stored PostgreSQL row differs from the browser submission.')
                if 'expected_current_nickname' in browser and rows[0]['current_nickname'] != browser['expected_current_nickname']:
                    raise RuntimeError('Current PostgreSQL player nickname differs from the browser setting.')
                evidence.append({'browser': browser['name'], 'matching_rows': len(rows), **rows[0]})
        result = {'passed': True, 'database': 'jumpbugi_local', 'browsers': evidence}
        destination = args.report.with_name('database-report.json')
        destination.write_text(json.dumps(result, default=str, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(result, default=str, indent=2))
    else:
        import psycopg
        from psycopg.rows import dict_row
        with psycopg.connect(connection_info(config), row_factory=dict_row) as connection:
            rows = connection.execute('SELECT player_id, count(*) AS runs FROM runs GROUP BY player_id ORDER BY player_id').fetchall()
        print(json.dumps(rows, default=str, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, subprocess.CalledProcessError, DatabaseError) as error:
        # Connection strings/passwords are never printed by this wrapper.
        print(f'Local setup could not complete: {type(error).__name__}. Check the local log/configuration.', file=sys.stderr)
        sys.exit(1)
