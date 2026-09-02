# Django API Convention Rules

> Version:
>
> - Python 3.11+
> - Django 5+
> - Django REST Framework
> - PostgreSQL

---

# 1. Project Structure

Use **Feature-First Architecture**, not Layer-First.

# 2. Naming Conventions

## Folders

Use:

```txt
snake_case
```

### Good

```txt
book_copy/
borrow_transaction/
```

### Bad

```txt
BookCopy/
borrowTransaction/
```

---

## Classes

Use:

```txt
PascalCase
```

### Good

```py
BookSerializer
BorrowService
UserViewSet
```

---

## Functions

Use:

```txt
snake_case
```

### Good

```py
borrow_book()
get_books()
```

### Bad

```py
BorrowBook()
```

---

## Constants

Use:

```txt
UPPER_CASE
```

### Example

```py
MAX_FINE_DAYS = 14
```

---

# 3. Model Rules

Models are responsible only for:

- data
- relations
- constraints

## Allowed

```py
@property
def is_overdue():
```

## Forbidden

```py
def process_payment():
```

Business logic must be moved to:

```txt
services/
```

---

All models must include:

```py
created_at
updated_at
```

Example:

```py
class TimestampMixin:
    created_at
    updated_at
```

---

# 4. Service Layer Rules

All business logic goes in the service layer.

## Forbidden

```py
serializer.save()
send_email()
```

## Preferred

```py
BorrowService.borrow()
FineService.pay()
```

Structure:

```txt
services/

borrow_book.py
return_book.py
pay_fine.py
```

---

# 5. Selector Rules

Selectors are for queries only.

## Selector

```py
get_active_books()
get_user_by_email()
```

### Responsibilities

✅ Read Data

❌ Update Data

---

## Service:

✅ Write Data

---

# 6. Serializer Rules

Serializers are only for:

- validate
- transform

## Forbidden

```py
def create():
    send_email()
```

Separate into:

```txt
BookInputSerializer
BookOutputSerializer
```

---

# 7. API Convention

Use:

```txt
/api/v1/
```

Example:

```txt
GET    /books
GET    /books/{id}

POST   /books

PATCH  /books/{id}

DELETE /books/{id}
```

---

## Rules

### Use plural nouns

Good:

```txt
/books
```

Bad:

```txt
/book
```

---

Do not use:

```txt
/getBooks
```

---

# 8. Response Convention

## Success

```json
{
  "success": true,
  "message": null,
  "data": {}
}
```

---

## Error

```json
{
  "success": false,
  "message": "Book not found",
  "errors": {}
}
```

---

## Pagination

```json
{
  "count": 100,
  "next": "",
  "previous": "",
  "results": []
}
```

---

# 9. Validation Order

Use this order:

```txt
Serializer
↓

Service
↓

Database
```

Do not validate in:

```txt
View
```

---

# 10. Authentication Rules

Format:

```txt
Bearer <token>
```

Flow:

```txt
Frontend
↓

Access Token
↓

Authorization Header
↓

Django
```

---

Permission classes:

```txt
IsMember
IsStaff
IsAdmin
```

Do not hardcode role checks.

---

# 11. Database Rules

Use:

- Foreign Key
- Index
- Unique
- Constraint

Example:

```py
email = models.EmailField(
    unique=True,
    db_index=True
)
```

---

## Migrations

Good:

```txt
0004_add_fine_status
```

Bad:

```txt
0005_auto
```

---

# 12. Logging Rules

Use:

```py
logger.info()

logger.warning()

logger.error()
```

Do not use:

```py
print()
```

Log format:

```txt
timestamp
service
user
message
```

---

# 13. Testing Rules

Structure:

```txt
tests/

test_models.py
test_services.py
test_views.py
```

Target:

```txt
Coverage ≥ 80%
```

Priority:

```txt
1. Service
2. API
3. Model
```

---

# 14. Git Convention

## Branches

```txt
feature/borrow-books

fix/fine-calculation

refactor/book-service
```

---

## Commits

```txt
feat:
fix:
refactor:
docs:
test:
chore:
```

Example:

```txt
feat: implement borrow transaction
```

---

# 15. Documentation Rules

Every app must have:

```txt
README.md
```

Contents:

```md
Purpose

Flow

Endpoints

Data Model
```

---

# 16. Forbidden Practices

❌ Fat Views

❌ Business Logic in Serializer

❌ Circular Import

❌ Raw SQL without justification

❌ Hardcoded ENV values

❌ Query in Loop

❌ Direct database access from frontend

---

# 17. Performance Rules

Use:

```py
select_related()

prefetch_related()
```

For relations.

Use:

```py
only()

defer()
```

For large datasets.

---

# 18. Security Rules

Do not commit:

```env
SECRET_KEY
```

Use:

```txt
.env
```

Production:

```txt
DEBUG=False
```

Use:

```txt
CORS
CSRF
Rate Limit
```

---

# 19. Code Review Checklist

Before merging:

- [ ] Tests pass
- [ ] No N+1 queries
- [ ] No hardcoded values
- [ ] API is consistent
- [ ] Documentation is updated
- [ ] Migrations are valid
- [ ] Naming follows convention
- [ ] No dead code

---

# Final Principle

> Models store data.
>
> Services run business logic.
>
> Selectors read data.
>
> Serializers validate data.
>
> Views handle HTTP.