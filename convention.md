# Django API Convention Rules

> Version:
>
> - Python 3.13+
> - Django 5+
> - Django REST Framework
> - PostgreSQL

---

# 1. Project Structure

Gunakan **Feature-First Architecture**, bukan Layer-First.

# 2. Naming Convention

## Folder

Gunakan:

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

## Class

Gunakan:

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

## Function

Gunakan:

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

## Constant

Gunakan:

```txt
UPPER_CASE
```

### Example

```py
MAX_FINE_DAYS = 14
```

---

# 3. Models Rules

Model bertanggung jawab hanya untuk:

- data
- relasi
- constraint

## Allowed

```py
@property
def is_overdue():
```

## Forbidden

```py
def process_payment():
```

Business logic harus dipindahkan ke:

```txt
services/
```

---

Semua model wajib memiliki:

```py
created_at
updated_at
```

Contoh:

```py
class TimestampMixin:
    created_at
    updated_at
```

---

# 4. Service Layer Rules

Semua business logic masuk ke service.

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

Struktur:

```txt
services/

borrow_book.py
return_book.py
pay_fine.py
```

---

# 5. Selector Rules

Selector hanya untuk query.

## Selector

```py
get_active_books()
get_user_by_email()
```

### Responsibilities

✅ Read Data

❌ Update Data

---

Service:

✅ Write Data

---

# 6. Serializer Rules

Serializer hanya:

- validate
- transform

## Forbidden

```py
def create():
    send_email()
```

Pisahkan:

```txt
BookInputSerializer
BookOutputSerializer
```

---

# 7. API Convention

Gunakan:

```txt
/api/v1/
```

Contoh:

```txt
GET    /books
GET    /books/{id}

POST   /books

PATCH  /books/{id}

DELETE /books/{id}
```

---

## Rules

### Gunakan plural

Good:

```txt
/books
```

Bad:

```txt
/book
```

---

Jangan gunakan:

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

Gunakan urutan:

```txt
Serializer
↓

Service
↓

Database
```

Jangan validasi di:

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

Permission:

```txt
IsMember
IsStaff
IsAdmin
```

Jangan hardcode role.

---

# 11. Database Rules

Gunakan:

- Foreign Key
- Index
- Unique
- Constraint

Contoh:

```py
email = models.EmailField(
    unique=True,
    db_index=True
)
```

---

Migration:

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

Gunakan:

```py
logger.info()

logger.warning()

logger.error()
```

Jangan gunakan:

```py
print()
```

Format log:

```txt
timestamp
service
user
message
```

---

# 13. Testing Rules

Struktur:

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

Prioritas:

```txt
1. Service
2. API
3. Model
```

---

# 14. Git Convention

## Branch

```txt
feature/borrow-books

fix/fine-calculation

refactor/book-service
```

---

## Commit

```txt
feat:
fix:
refactor:
docs:
test:
chore:
```

Contoh:

```txt
feat: implement borrow transaction
```

---

# 15. Documentation Rules

Setiap app wajib memiliki:

```txt
README.md
```

Isi:

```md
Purpose

Flow

Endpoints

Data Model
```

---

# 16. Forbidden Practices

❌ Fat Views

❌ Business Logic di Serializer

❌ Circular Import

❌ Raw SQL tanpa alasan

❌ Hardcoded ENV

❌ Query dalam loop

❌ Direct database access dari frontend

---

# 17. Performance Rules

Gunakan:

```py
select_related()

prefetch_related()
```

Untuk relasi.

Gunakan:

```py
only()

defer()
```

Untuk data besar.

---

# 18. Security Rules

Jangan commit:

```env
SECRET_KEY
```

Gunakan:

```txt
.env
```

Production:

```txt
DEBUG=False
```

Gunakan:

```txt
CORS
CSRF
Rate Limit
```

---

# 19. Code Review Checklist

Sebelum merge:

- [ ] Test lulus
- [ ] Tidak ada query N+1
- [ ] Tidak ada hardcoded value
- [ ] API konsisten
- [ ] Dokumentasi diperbarui
- [ ] Migration valid
- [ ] Naming sesuai convention
- [ ] Tidak ada dead code

---

# Final Principle

> Model menyimpan data.
>
> Service menjalankan bisnis.
>
> Selector membaca data.
>
> Serializer memvalidasi data.
>
> View mengatur HTTP.