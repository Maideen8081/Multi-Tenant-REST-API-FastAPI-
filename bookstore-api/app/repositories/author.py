from app.models.author import Author
from app.repositories.base import TenantScopedRepository


class AuthorRepository(TenantScopedRepository[Author]):
    def __init__(self):
        super().__init__(Author)


author_repo = AuthorRepository()
