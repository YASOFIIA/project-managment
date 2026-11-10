# REFERENCE_NOTES.md

Примерный проект от препода (`epam_campus_final_task-main`) лежит **вне этого репозитория**.
Используй его как справочник: читать можно, копировать нельзя. Если берёшь идею, пиши свою
реализацию и объясняй её своими словами.

Пути ниже относятся к его проекту.

| Твоя задача | Что почитать у него | На что смотреть |
|---|---|---|
| T0.x структура | `pyproject.toml`, `src/app/main.py`, `src/app/core/config.py` | как собран `create_app()`, как настройки читаются из env |
| T1.1 модели | `src/app/models/*.py` | ограничения, связи, `ON DELETE CASCADE`, роль как enum |
| T1.2 миграции | `src/app/db/migrations/versions/0001_initial_schema.py`, `alembic.ini` | что генерирует Alembic |
| T2.x auth | `src/app/core/security.py`, `src/app/api/auth.py`, `src/app/api/deps.py` | хеширование, создание и проверка JWT, зависимость `get_current_user` |
| T3.1 права | `src/app/services/access.py` | матрица прав в docstring, 404 вместо 403 для чужих проектов |
| T3.x проекты | `src/app/services/projects.py`, `src/app/api/projects.py` | разделение роутера и бизнес-логики |
| T4.x документы | `src/app/services/uploads.py`, `src/app/storage/*.py` | проверка magic bytes, интерфейс хранилища |
| T6.x ошибки | `src/app/core/errors.py`, `src/app/api/errors.py` | единый формат `{"detail", "code"}` |
| тесты | `tests/conftest.py`, `tests/database.py`, `tests/api/conftest.py` | схема с откатом после каждого теста |

## Чего у него НЕТ (это делаем сами)

- Docker, docker-compose, CI/CD, README
- S3, Lambda, лимит размера проекта
- Часть запросов на чистом SQL, `schema.sql`
- Нормализация и денормализация с описанием
- `POST /auth` с repeat password, пути в твоём формате (`/project/<id>/...`)

## Где он принял решения, с которыми можно не согласиться

- Участник не может удалять документы (у тебя в задании «can modify, cannot delete» - уточни
  у ментора, относится ли запрет к проекту или и к документам).
- Все ошибки валидации пока в стандартном формате FastAPI (он сам отметил это в HANDOVER.md).
