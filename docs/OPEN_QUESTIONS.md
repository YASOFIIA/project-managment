# OPEN_QUESTIONS.md

Вопросы, которые лучше уточнить у ментора. Пока ответа нет, агент работает по значению
"по умолчанию" и не выдумывает своих решений.

| # | Вопрос | По умолчанию, пока нет ответа |
|---|---|---|
| 1 | "Creation of db with and without ORM": правильно ли, что часть запросов делается через ORM, а часть сырым SQL, плюс схема написана и через модели, и в `schema.sql`? | Да, так и делаем |
| 2 | Можно ли использовать `uv` + `pyproject.toml` вместо poetry/tox? Нужен ли именно tox? | uv, плюс tox-конфиг, если останется время |
| 3 | Участник проекта может удалять документы или только редактировать (не удалять сам проект)? | Участник может удалять документы, не может удалять проект и управлять доступом |
| 4 | Пути в единственном числе (`/project/<id>/info`, `/document/<id>`) оставляем как в ТЗ? | Да, как в ТЗ |
| 5 | Как должен работать лимит размера в Lambda: какой лимит, что делать с файлом, который его превысил? | Лимит 50 MB на проект; Lambda удаляет превысивший файл и сообщает API |
| 6 | Нужно ли optional `share by email` и ресайз картинок? | Не делаем, если не хватит времени |
| 7 | Какой вариант деплоя ожидается: ECS, EC2 или что-то проще? | Решим после базового проекта |
| 8 | Может ли участник (`participant`) менять `name` и `description` проекта (`PUT /project/<id>/info`)? В ТЗ явно ограничены только удаление проекта и инвайты. | Разрешено (участник может редактировать метаданные проекта наряду с владельцем) |

## Готовое сообщение ментору (можно переслать, переведи при необходимости)

```
Hi! Before I start, a few clarifying questions about the final task:
1. "DB with and without ORM": is it OK if the app uses SQLAlchemy ORM for most queries, and
   a part of the queries (e.g. GET /projects with a JOIN, project size sum) is written as raw
   SQL, plus a hand-written schema.sql next to the Alembic migration?
2. Is uv + pyproject.toml acceptable instead of poetry/tox?
3. Can a participant delete documents, or only the owner (participants cannot delete the
   project itself)?
4. For the Lambda size limit: is a per-project limit (e.g. 50 MB) fine, and should the Lambda
   delete the file that exceeds it?
5. For deployment: ECS or EC2, or is something simpler fine?
6. Can a participant update project info (name/description via PUT /project/<id>/info),
   or should that also be restricted to the owner (the assignment only explicitly restricts
   project deletion and inviting new members)?
Thanks!
```
