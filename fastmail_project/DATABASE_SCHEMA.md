# 📚 Полное руководство по базе данных FastMail

## Обзор структуры БД

База данных SQLite (`db.sqlite3`) содержит **14 таблиц**, которые можно разделить на 3 группы:

1. **Таблицы приложения FastMail** (3 таблицы)
2. **Таблицы аутентификации Django** (6 таблиц)
3. **Служебные таблицы Django** (4 таблицы)

---

## 1️⃣ ТАБЛИЦЫ ПРИЛОЖЕНИЯ FASTMAIL

### 📁 `core_profile` — Профили пользователей

**Назначение:** Связывает стандартных пользователей Django с их email-адресами в системе.

| Столбец | Тип | Описание |
|---------|-----|----------|
| `id` 🔑 | INTEGER | Первичный ключ (автоинкремент) |
| `user_id` | INTEGER | 🔗 Внешний ключ → `auth_user.id` (OneToOne) |
| `email_address` | VARCHAR(254) | Уникальный email пользователя |
| `created_at` | DATETIME | Дата создания профиля |

**Пример использования:**
```python
# Найти пользователя по email
profile = Profile.objects.get(email_address='admin@example.com')
user = profile.user  # Получаем объект User
print(user.username)  # 'admin'
```

**Связи:**
- `user_id` → `auth_user.id` (OneToOne: один профиль у одного пользователя)

---

### 📁 `core_folder` — Папки для писем

**Назначение:** Хранит системные и пользовательские папки.

| Столбец | Тип | Описание |
|---------|-----|----------|
| `id` 🔑 | INTEGER | Первичный ключ (автоинкремент) |
| `name` | VARCHAR(50) | Название папки (уникальное) |
| `owner_id` | INTEGER | 🔗 Внешний ключ → `auth_user.id` (NULL для системных папок) |

**Типы папок:**

1. **Системные папки** (`owner_id = NULL`):
   - `Inbox` — Входящие
   - `Sent` — Отправленные
   - `Archive` — Архив
   - `Trash` — Корзина
   - `Drafts` — Черновики

2. **Пользовательские папки** (`owner_id = ID_пользователя`):
   - Создаются пользователями динамически

**Пример использования:**
```python
# Получить системную папку
inbox = Folder.objects.get(name='Inbox', owner=None)

# Создать пользовательскую папку
work_folder = Folder.objects.create(name='Work', owner=user)
```

---

### 📁 `core_email` — Письма

**Назначение:** Хранит все email-сообщения пользователей.

| Столбец | Тип | Описание |
|---------|-----|----------|
| `id` 🔑 | INTEGER | Первичный ключ (автоинкремент) |
| `owner_id` | INTEGER | 🔗 Внешний ключ → `auth_user.id` (владелец письма) |
| `folder_id` | BIGINT | 🔗 Внешний ключ → `core_folder.id` (папка) |
| `sender` | VARCHAR(254) | Email отправителя |
| `recipient` | VARCHAR(254) | Email получателя |
| `subject` | VARCHAR(255) | Тема письма |
| `body` | TEXT | Текст сообщения |
| `is_read` | BOOL | Флаг прочтения (True/False) |
| `is_deleted` | BOOL | Флаг удаления (soft delete) |
| `created_at` | DATETIME | Дата создания (авто) |
| `updated_at` | DATETIME | Дата обновления (авто) |

**Индексы для оптимизации:**
- `owner_deleted_idx` — по полям `(owner_id, is_deleted)`
- `folder_deleted_idx` — по полям `(folder_id, is_deleted)`

**Пример использования:**
```python
# Получить все непрочитанные письма из Inbox
unread = Email.objects.filter(
    owner=user,
    folder__name='Inbox',
    is_read=False,
    is_deleted=False
)

# Пометить письмо как прочитанное
email.is_read = True
email.save(update_fields=['is_read', 'updated_at'])
```

**Жизненный цикл письма:**
```
1. Создание → is_deleted=False, is_read=False
2. Просмотр → is_read=True
3. Перемещение → folder_id меняется
4. Удаление → is_deleted=True (soft delete)
```

---

## 2️⃣ ТАБЛИЦЫ АУТЕНТИФИКАЦИИ DJANGO

### 📁 `auth_user` — Пользователи

**Назначение:** Стандартная модель пользователей Django.

| Столбец | Тип | Описание |
|---------|-----|----------|
| `id` 🔑 | INTEGER | Первичный ключ |
| `password` | VARCHAR(128) | Хэш пароля |
| `username` | VARCHAR(150) | Имя пользователя (уникальное) |
| `email` | VARCHAR(254) | Email (не уникальное в этой таблице) |
| `first_name` | VARCHAR(150) | Имя |
| `last_name` | VARCHAR(150) | Фамилия |
| `is_superuser` | BOOL | Суперпользователь (доступ ко всему) |
| `is_staff` | BOOL | Доступ в админку Django |
| `is_active` | BOOL | Активен ли аккаунт |
| `last_login` | DATETIME | Последний вход |
| `date_joined` | DATETIME | Дата регистрации |

**В проекте создано 3 пользователя:**
- `admin` (superuser, is_staff=True)
- `user1` (обычный пользователь)
- `user2` (обычный пользователь)

---

### 📁 `auth_group` — Группы пользователей

**Назначение:** Группировка пользователей для массового назначения прав.

| Столбец | Тип | Описание |
|---------|-----|----------|
| `id` 🔑 | INTEGER | Первичный ключ |
| `name` | VARCHAR(150) | Название группы |

**В проекте:** Не используется (0 записей)

---

### 📁 `auth_permission` — Права доступа

**Назначение:** Описывает все возможные действия в системе.

| Столбец | Тип | Описание |
|---------|-----|----------|
| `id` 🔑 | INTEGER | Первичный ключ |
| `content_type_id` | INTEGER | 🔗 → `django_content_type.id` |
| `codename` | VARCHAR(100) | Код права (напр., `add_email`, `delete_email`) |
| `name` | VARCHAR(255) | Человекочитаемое название |

**Примеры прав:**
- `core | email | Can add email`
- `core | email | Can change email`
- `core | email | Can delete email`
- `core | email | Can view email`

**В проекте:** 36 прав (автоматически создаются Django)

---

### 📁 `auth_user_groups` — Связь пользователей и групп

**Назначение:** Many-to-Many связь между пользователями и группами.

| Столбец | Тип | Описание |
|---------|-----|----------|
| `id` 🔑 | INTEGER | Первичный ключ |
| `user_id` | INTEGER | 🔗 → `auth_user.id` |
| `group_id` | INTEGER | 🔗 → `auth_group.id` |

**В проекте:** Не используется (0 записей)

---

### 📁 `auth_user_user_permissions` — Персональные права

**Назначение:** Индивидуальные права пользователей (помимо групповых).

| Столбец | Тип | Описание |
|---------|-----|----------|
| `id` 🔑 | INTEGER | Первичный ключ |
| `user_id` | INTEGER | 🔗 → `auth_user.id` |
| `permission_id` | INTEGER | 🔗 → `auth_permission.id` |

**В проекте:** Не используется (0 записей)

---

### 📁 `auth_group_permissions` — Права групп

**Назначение:** Many-to-Many связь между группами и правами.

| Столбец | Тип | Описание |
|---------|-----|----------|
| `id` 🔑 | INTEGER | Первичный ключ |
| `group_id` | INTEGER | 🔗 → `auth_group.id` |
| `permission_id` | INTEGER | 🔗 → `auth_permission.id` |

**В проекте:** Не используется (0 записей)

---

## 3️⃣ СЛУЖЕБНЫЕ ТАБЛИЦЫ DJANGO

### 📁 `django_content_type` — Типы контента

**Назначение:** Сопоставляет модели Django с таблицами БД.

| Столбец | Тип | Описание |
|---------|-----|----------|
| `id` 🔑 | INTEGER | Первичный ключ |
| `app_label` | VARCHAR(100) | Название приложения (напр., `core`, `auth`) |
| `model` | VARCHAR(100) | Название модели (напр., `email`, `user`) |

**Примеры:**
- `auth | user`
- `core | email`
- `core | folder`
- `core | profile`

---

### 📁 `django_migrations` — Миграции

**Назначение:** Отслеживает применённые миграции БД.

| Столбец | Тип | Описание |
|---------|-----|----------|
| `id` 🔑 | INTEGER | Первичный ключ |
| `app` | VARCHAR(255) | Приложение |
| `name` | VARCHAR(255) | Название миграции |
| `applied` | DATETIME | Дата применения |

**В проекте:** 20 применённых миграций

---

### 📁 `django_session` — Сессии пользователей

**Назначение:** Хранит активные сессии (для аутентификации).

| Столбец | Тип | Описание |
|---------|-----|----------|
| `session_key` 🔑 | VARCHAR(40) | Уникальный ключ сессии |
| `session_data` | TEXT | Сериализованные данные сессии |
| `expire_date` | DATETIME | Дата истечения сессии |

**В проекте:** 2 активные сессии (от тестовых входов)

---

### 📁 `django_admin_log` — Журнал админки

**Назначение:** Логирует действия в Django Admin.

| Столбец | Тип | Описание |
|---------|-----|----------|
| `id` 🔑 | INTEGER | Первичный ключ |
| `user_id` | INTEGER | 🔗 → `auth_user.id` |
| `content_type_id` | INTEGER | 🔗 → `django_content_type.id` |
| `object_id` | TEXT | ID изменённого объекта |
| `object_repr` | VARCHAR(200) | Представление объекта |
| `action_flag` | SMALLINT | Тип действия (1=add, 2=change, 3=delete) |
| `change_message` | TEXT | Описание изменений |
| `action_time` | DATETIME | Время действия |

**В проекте:** Не использовалась (0 записей)

---

### 📁 `sqlite_sequence` — Автоинкремент SQLite

**Назначение:** Служебная таблица SQLite для автоинкремента ID.

| Столбец | Тип | Описание |
|---------|-----|----------|
| `name` | TEXT | Название таблицы |
| `seq` | INTEGER | Следующее значение ID |

---

### 📁 `django_content_type` — Типы контента

**Назначение:** Сопоставляет модели Django с таблицами БД.

| Столбец | Тип | Описание |
|---------|-----|----------|
| `id` 🔑 | INTEGER | Первичный ключ |
| `app_label` | VARCHAR(100) | Название приложения |
| `model` | VARCHAR(100) | Название модели |

**В проекте:** 9 записей (по количеству моделей)

---

## 📊 ER-Диаграмма (связи между таблицами)

```
┌─────────────────┐
│   auth_user     │
│  (Пользователи) │
└────────┬────────┘
         │
    ┌────┴────┬──────────────┬─────────────────┐
    │         │              │                 │
    ▼         ▼              ▼                 ▼
┌─────────┐ ┌──────────┐ ┌─────────────┐ ┌──────────┐
│core_    │ │core_     │ │auth_user_   │ │django_   │
│profile  │ │email     │ │user_permiss.│ │admin_log │
└────┬────┘ └────┬─────┘ └─────────────┘ └──────────┘
     │           │
     │      ┌────┴────┐
     │      │         │
     │      ▼         ▼
     │  ┌─────────┐ ┌──────────┐
     └─▶│core_    │◀───────────┘
        │folder   │
        └─────────┘
```

---

## 🔍 Полезные SQL-запросы

### Получить все письма пользователя с именами папок
```sql
SELECT 
    e.subject,
    e.sender,
    e.recipient,
    e.is_read,
    f.name as folder_name,
    e.created_at
FROM core_email e
LEFT JOIN core_folder f ON e.folder_id = f.id
WHERE e.owner_id = 1 AND e.is_deleted = 0
ORDER BY e.created_at DESC;
```

### Получить количество писем по папкам
```sql
SELECT 
    f.name,
    COUNT(e.id) as email_count,
    SUM(CASE WHEN e.is_read = 0 THEN 1 ELSE 0 END) as unread_count
FROM core_folder f
LEFT JOIN core_email e ON f.id = e.folder_id 
    AND e.owner_id = 1 
    AND e.is_deleted = 0
WHERE f.owner_id IS NULL  -- только системные папки
GROUP BY f.id, f.name;
```

### Получить всех пользователей и их email
```sql
SELECT 
    u.username,
    u.email,
    p.email_address as profile_email,
    u.is_superuser,
    u.last_login
FROM auth_user u
LEFT JOIN core_profile p ON u.id = p.user_id;
```

---

## 💡 Рекомендации

### Для разработки:
```bash
# Просмотр структуры БД
python manage.py dbshell
sqlite> .schema

# Или через Python
python manage.py shell
>>> from core.models import Email, Folder, Profile
>>> Email.objects.all().count()
```

### Для отладки:
```bash
# Экспорт БД в дамп
python manage.py dumpdata core auth --format json > backup.json

# Импорт из дампа
python manage.py loaddata backup.json
```
