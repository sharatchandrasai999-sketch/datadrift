# Contributing

Thanks for helping. Dataset drift detector comparing two CSVs (schema changes and numeric drift). This is a small, personal project, so keep changes small and easy to review.

## Before you send a change

- Run the tests from any folder: `pytest -q` (tests must not depend on the current working directory)
- Keep the offline path working: comparing two local CSVs must need no API key and no download.
- If you add a check, ship a pair of small example CSVs that exercise it.

## Reporting a problem

Open an issue and include:

- The exact command you ran
- The input file, if it is about one
- What happened, and what you expected instead

Do not include API keys, private documents, or personal details.
