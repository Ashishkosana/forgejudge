"""Idempotently seed the five starter coding problems."""

from typing import TypedDict

from backend.models import Problem, TestCase
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class SeedProblem(TypedDict):
    slug: str
    title: str
    difficulty: str
    description: str
    cases: list[tuple[str, str, bool]]


PROBLEMS: tuple[SeedProblem, ...] = (
    {
        "slug": "sum-of-two-numbers",
        "title": "Sum of Two Numbers",
        "difficulty": "easy",
        "description": (
            "Read two integers from standard input and print their sum.\n\n"
            "Input: two space-separated integers.\nOutput: their sum."
        ),
        "cases": [
            ("2 3\n", "5\n", True),
            ("-4 9\n", "5\n", True),
            ("0 0\n", "0\n", False),
        ],
    },
    {
        "slug": "reverse-a-string",
        "title": "Reverse a String",
        "difficulty": "easy",
        "description": (
            "Read one line and print its characters in reverse order.\n\n"
            "Input: one line of text.\nOutput: the reversed line."
        ),
        "cases": [
            ("forge\n", "egrof\n", True),
            ("a\n", "a\n", True),
            ("\n", "\n", False),
        ],
    },
    {
        "slug": "count-vowels",
        "title": "Count the Vowels",
        "difficulty": "easy",
        "description": (
            "Count the English vowels in a line, case-insensitively.\n\n"
            "Input: one line of text.\nOutput: the number of vowels."
        ),
        "cases": [
            ("ForgeJudge\n", "4\n", True),
            ("rhythm\n", "0\n", True),
            ("AEIOU\n", "5\n", False),
        ],
    },
    {
        "slug": "two-sum",
        "title": "Two Sum",
        "difficulty": "medium",
        "description": (
            "Given a list of integers and a target, print the zero-based indices of two distinct "
            "values whose sum equals the target. Exactly one solution exists.\n\n"
            "Input: n, then n integers, then target.\nOutput: two indices in ascending order."
        ),
        "cases": [
            ("4\n2 7 11 15\n9\n", "0 1\n", True),
            ("3\n3 2 4\n6\n", "1 2\n", True),
            ("2\n3 3\n6\n", "0 1\n", False),
        ],
    },
    {
        "slug": "longest-unique-substring",
        "title": "Longest Unique Substring",
        "difficulty": "medium",
        "description": (
            "Print the length of the longest substring containing no repeated characters.\n\n"
            "Input: one line of text.\nOutput: one integer."
        ),
        "cases": [
            ("abcabcbb\n", "3\n", True),
            ("bbbbb\n", "1\n", True),
            ("pwwkew\n", "3\n", False),
        ],
    },
)


async def seed_problems(session: AsyncSession) -> int:
    inserted = 0
    for data in PROBLEMS:
        existing = await session.scalar(select(Problem).where(Problem.slug == data["slug"]))
        if existing is not None:
            continue
        problem = Problem(
            slug=str(data["slug"]),
            title=str(data["title"]),
            difficulty=str(data["difficulty"]),
            description=str(data["description"]),
            is_published=True,
        )
        session.add(problem)
        await session.flush()
        for case_position, (input_data, expected_output, is_sample) in enumerate(data["cases"]):
            session.add(
                TestCase(
                    problem_id=problem.id,
                    position=case_position,
                    input_data=input_data,
                    expected_output=expected_output,
                    is_sample=is_sample,
                )
            )
        inserted += 1
    await session.commit()
    return inserted
