"""Seed the local ForgeJudge problem catalog."""

import asyncio

from backend.common.database import SessionFactory, engine
from backend.services.seed import seed_problems


async def main() -> None:
    try:
        async with SessionFactory() as session:
            inserted = await seed_problems(session)
        print(f"Seed complete: inserted {inserted} problems")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
