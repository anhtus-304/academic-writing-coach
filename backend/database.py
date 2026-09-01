import sys
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

try:
    from backend.config import settings
except ImportError:
    from config import settings

if "backend.database" in sys.modules and __name__ == "database":
    _mod = sys.modules["backend.database"]
    engine = _mod.engine
    AsyncSessionLocal = _mod.AsyncSessionLocal
    Base = _mod.Base
    get_db = _mod.get_db
elif "database" in sys.modules and __name__ == "backend.database":
    _mod = sys.modules["database"]
    engine = _mod.engine
    AsyncSessionLocal = _mod.AsyncSessionLocal
    Base = _mod.Base
    get_db = _mod.get_db
else:
    engine = create_async_engine(
        settings.SQLALCHEMY_DATABASE_URI,
        echo=False,
        future=True,
        pool_pre_ping=True,
    )

    AsyncSessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    Base = declarative_base()

    async def get_db() -> AsyncSession:
        async with AsyncSessionLocal() as session:
            yield session