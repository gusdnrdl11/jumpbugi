"""Local browser-game API backed by PostgreSQL; browser IDs are not authentication."""
from contextlib import asynccontextmanager, contextmanager
import os
from pathlib import Path
from typing import Annotated, Literal
from unicodedata import category
from uuid import UUID

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import psycopg
from psycopg.rows import dict_row
from pydantic import (
    AwareDatetime, BaseModel, ConfigDict, Field, StrictInt, StringConstraints,
    field_validator,
)


SERVER_DIR = Path(__file__).resolve().parent
Nickname = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=12)]
HistoricalNickname = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
Version = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
UNAVAILABLE = "Local database is unavailable."


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    @field_validator("*")
    @classmethod
    def reject_null_characters(cls, value):
        if isinstance(value, str) and "\x00" in value:
            raise ValueError("Null characters are not allowed.")
        return value


class PlayerInput(InputModel):
    player_id: UUID
    nickname: Nickname

    @field_validator("nickname", mode="before")
    @classmethod
    def reject_invisible_nickname_characters(cls, value):
        if isinstance(value, str) and any(category(char) in {"Cc", "Cf", "Cs", "Zl", "Zp"} for char in value):
            raise ValueError("Nickname cannot contain control, format, or line separator characters.")
        return value


class RunInput(InputModel):
    player_id: UUID
    # Runs preserve their submitted nickname, including older queued results.
    # Updating a player's display name must not change run identity or retries.
    nickname: HistoricalNickname
    run_id: UUID
    score: Annotated[StrictInt, Field(ge=0, le=9_007_199_254_740_991)]
    survival_time: Annotated[float, Field(ge=0, le=315_360_000)]
    game_version: Version
    played_at: AwareDatetime
    death_obstacle: Annotated[str | None, Field(max_length=100)] = None
    max_speed: Annotated[float, Field(ge=0, le=1_000_000)] = 1
    device_type: Literal["desktop", "mobile"] = "desktop"

    @field_validator("survival_time", "max_speed", mode="before")
    @classmethod
    def require_json_number(cls, value):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("A finite JSON number is required.")
        return value

    @field_validator("played_at", mode="before")
    @classmethod
    def require_timestamp_string(cls, value):
        if not isinstance(value, str) or len(value) > 100:
            raise ValueError("An ISO timestamp with a timezone is required.")
        return value


def create_app(database_url: str | None = None) -> FastAPI:
    url = os.environ.get("DATABASE_URL") if database_url is None else database_url
    schema = (SERVER_DIR / "schema.sql").read_text(encoding="utf-8")
    initialized = False

    @contextmanager
    def database():
        nonlocal initialized
        if not url:
            raise HTTPException(503, UNAVAILABLE)
        try:
            # Each request owns its connection: commit on success, rollback on error,
            # and always close. No connection or transaction is shared by requests.
            with psycopg.connect(url, row_factory=dict_row, connect_timeout=3) as connection:
                if not initialized:
                    connection.execute(schema, prepare=False)
                yield connection
            initialized = True
        except psycopg.Error:
            # Keep credentials, DSNs and database internals out of HTTP responses.
            raise HTTPException(503, UNAVAILABLE) from None

    @asynccontextmanager
    async def lifespan(app):
        try:
            with database() as connection:
                connection.execute("SELECT 1")
        except HTTPException:
            # Static files remain available; API requests check the DB and return 503.
            pass
        yield

    app = FastAPI(title="Jump Bugi local API", version="0.1.0", lifespan=lifespan)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, exc):
        # JSONResponse cannot encode NaN/Infinity even when they occur in rejected
        # input. Report locations and messages without echoing untrusted values.
        return JSONResponse(status_code=422, content={"detail": [
            {"type": error["type"], "loc": list(error["loc"]), "msg": error["msg"]}
            for error in exc.errors()
        ]})

    @app.get("/api/health")
    def health():
        with database() as connection:
            connection.execute("SELECT 1").fetchone()
        return {"status": "ok", "database": "ok"}

    @app.post("/api/players", status_code=201)
    def register_player(player: PlayerInput, response: Response):
        with database() as connection:
            row = connection.execute(
                "INSERT INTO players (player_id, nickname) VALUES (%s, %s) "
                "ON CONFLICT (player_id) DO NOTHING RETURNING *",
                (player.player_id, player.nickname),
            ).fetchone()
            if row is None:
                row = connection.execute(
                    "UPDATE players SET nickname = %s WHERE player_id = %s RETURNING *",
                    (player.nickname, player.player_id),
                ).fetchone()
                response.status_code = 200
        return row

    @app.post("/api/runs", status_code=201)
    def record_run(run: RunInput, response: Response):
        values = run.model_dump()
        with database() as connection:
            existing = connection.execute(
                "SELECT * FROM runs WHERE run_id = %s", (run.run_id,),
            ).fetchone()
            if existing is None:
                player = connection.execute(
                    "SELECT player_id FROM players WHERE player_id = %s", (run.player_id,),
                ).fetchone()
                if player is None:
                    raise HTTPException(404, "Player is not registered.")
                row = connection.execute(
                    "INSERT INTO runs (player_id, nickname, run_id, score, survival_time, "
                    "game_version, played_at, death_obstacle, max_speed, device_type) "
                    "VALUES (%(player_id)s, %(nickname)s, %(run_id)s, %(score)s, "
                    "%(survival_time)s, %(game_version)s, %(played_at)s, "
                    "%(death_obstacle)s, %(max_speed)s, %(device_type)s) "
                    "ON CONFLICT (run_id) DO NOTHING RETURNING *",
                    values,
                ).fetchone()
                if row is not None:
                    return row
                # Another request may have committed the same ID after the SELECT.
                existing = connection.execute(
                    "SELECT * FROM runs WHERE run_id = %s", (run.run_id,),
                ).fetchone()
            if existing is None or any(existing[key] != value for key, value in values.items()):
                raise HTTPException(409, "Run ID already belongs to a different result.")
            response.status_code = 200
            return existing

    @app.get("/api/runs")
    def list_runs(player_id: UUID, limit: Annotated[int, Query(ge=1, le=50)] = 50):
        with database() as connection:
            rows = connection.execute(
                "SELECT * FROM runs WHERE player_id = %s "
                "ORDER BY played_at DESC, run_id ASC LIMIT %s", (player_id, limit),
            ).fetchall()
        return {"items": rows}

    @app.get("/api/leaderboard")
    def leaderboard(limit: Annotated[int, Query(ge=1, le=100)] = 5):
        with database() as connection:
            rows = connection.execute(
                "SELECT best_runs.run_id, best_runs.player_id, players.nickname, "
                "best_runs.score, best_runs.survival_time, best_runs.game_version, "
                "best_runs.played_at, best_runs.death_obstacle, best_runs.max_speed, "
                "best_runs.device_type, best_runs.received_at "
                "FROM (SELECT DISTINCT ON (player_id) * FROM runs "
                "ORDER BY player_id, score DESC, survival_time DESC, played_at ASC, run_id ASC) "
                "AS best_runs JOIN players ON players.player_id = best_runs.player_id "
                "ORDER BY best_runs.score DESC, best_runs.survival_time DESC, "
                "best_runs.played_at ASC, best_runs.run_id ASC "
                "LIMIT %s", (limit,),
            ).fetchall()
        return {"items": rows}

    # API routes must precede this catch-all mount. GitHub Pages continues to serve
    # the same web directory independently without a Python runtime.
    app.mount("/", StaticFiles(directory=SERVER_DIR.parent / "web", html=True), name="web")
    return app


app = create_app()
