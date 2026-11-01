# Контракт HTTP API между Telegram-ботом и 1С

Базовый адрес в примерах: `/tg_project/hs/issue-api/v1`.

## Общие правила

- кодировка: UTF-8;
- формат тела и ответа: `application/json`;
- бот передаёт `X-API-Key: <секрет>`;
- успешные ответы имеют HTTP-код 2xx;
- ошибка возвращается как `{"error": "понятное описание"}`;
- даты передаются в ISO 8601, например `2026-11-01T14:30:00+03:00`.

## Получить категории

`GET /categories`

```json
{
  "items": [
    {"id": "technical", "name": "Техническая проблема"},
    {"id": "access", "name": "Доступ и учётные записи"}
  ]
}
```

## Создать заявку

`POST /issues`

```json
{
  "telegram_user_id": 123456789,
  "telegram_username": "student",
  "telegram_full_name": "Иван Иванов",
  "category_id": "technical",
  "subject": "Не открывается база",
  "description": "При запуске появляется сообщение об ошибке",
  "priority": "normal"
}
```

Ответ `201 Created`:

```json
{
  "id": "a5ba25c0-9d2f-4a55-9e47-893a83cc7d4d",
  "number": "000000012",
  "status": "new",
  "status_name": "Новая",
  "created_at": "2026-11-01T14:30:00+03:00"
}
```

## Получить заявки пользователя

`GET /issues?telegram_user_id=123456789&limit=10`

```json
{
  "items": [
    {
      "id": "a5ba25c0-9d2f-4a55-9e47-893a83cc7d4d",
      "number": "000000012",
      "category_name": "Техническая проблема",
      "subject": "Не открывается база",
      "priority": "normal",
      "priority_name": "Обычный",
      "status": "new",
      "status_name": "Новая",
      "created_at": "2026-11-01T14:30:00+03:00"
    }
  ]
}
```

## Получить заявку

`GET /issues/{id}?telegram_user_id=123456789`

Возвращает полную карточку заявки. `telegram_user_id` нужен, чтобы один пользователь
Telegram не мог получить чужую заявку.

## Отменить заявку

`POST /issues/{id}/cancel`

```json
{"telegram_user_id": 123456789}
```

Отмена допускается только для статуса `new`. Ответ содержит обновлённую карточку.

## Справочные значения

Приоритеты: `low`, `normal`, `high`.

Статусы первой версии: `new`, `in_progress`, `completed`, `rejected`, `cancelled`.

