import asyncio
from app.models import Base
from sqlalchemy.ext.asyncio import create_async_engine

async def main():
    engine = create_async_engine("sqlite+aiosqlite:///./aevix.db")
    async with engine.begin() as conn:
        # Import compiler override for JSONB on sqlite
        from sqlalchemy.ext.compiler import compiles
        from sqlalchemy.dialects.postgresql import JSONB
        @compiles(JSONB, "sqlite")
        def _compile_jsonb_sqlite(type_, compiler, **kw):
            return "JSON"
            
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables initialized successfully in aevix.db!")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
