import asyncio

async def test_all():
    # Test Redis
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url('redis://127.0.0.1:6379/0')
        await r.ping()
        print('Redis: CONNECTED')
        await r.aclose()
    except Exception as e:
        print(f'Redis error: {e}')

    # Test PostgreSQL
    try:
        import asyncpg
        conn = await asyncpg.connect(
            user='aevix',
            password='aevix',
            host='127.0.0.1',
            port=5432,
            database='aevix'
        )
        version = await conn.fetchval('SELECT version()')
        print(f'PostgreSQL connected: {version}')
        await conn.close()
    except Exception as e:
        print(f'PostgreSQL error: {e}')

asyncio.run(test_all())
