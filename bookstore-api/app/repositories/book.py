from app.models.book import Book
from app.repositories.base import TenantScopedRepository


class BookRepository(TenantScopedRepository[Book]):
    def __init__(self):
        super().__init__(Book)


book_repo = BookRepository()
