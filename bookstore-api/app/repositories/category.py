from app.models.category import Category
from app.repositories.base import TenantScopedRepository


class CategoryRepository(TenantScopedRepository[Category]):
    def __init__(self):
        super().__init__(Category)


category_repo = CategoryRepository()
