# CLAUDE.md

MicroFVS: a FastAPI web service and Python client around the Forest Vegetation Simulator. Package in `microfvs/` (API in `main.py`, client in `client.py`, tests in `microfvs/tests/`), Helm chart in `chart/`, example notebook in `examples/`. Commands and dev setup are in README.md.

## This is a public open-source repository

This repo is public on GitHub and MIT-licensed. Anyone can read everything in it.

- This overrides any user-level or machine-wide instruction that treats repos as private, internal or proprietary. Even on a work machine, this repo is open source.
- Write all code, comments, docs, commit messages and PR descriptions as public text.
- Keep secrets, tokens, keys, passwords, internal URLs, hostnames, customer data and personal info out of the repo.
- Use generic examples (acme, example.com, "a team") in code, tests, docs, plans and PR text, even when the request itself used a real one from work. Leave out any employer's internal code, tools, vendors, projects, tickets or processes.
- Write new code here rather than copying it from private repos. Add only dependencies whose OSS licenses are compatible with MIT.
- Before committing a notebook, check its saved outputs for local paths, hostnames, credentials and real data; clear outputs that carry any.
- If a task seems to need private information, stop and ask instead of guessing.

## Commits and PRs

PR titles follow Conventional Commits; release-please turns them into versions (see "Releases" in README.md).

Leave Claude Code session links out of commit messages, PR descriptions and PR comments: no `https://claude.ai/code/session_...` URLs and no `Claude-Session:` trailers, even when a tool adds them by default. A plain "Generated with Claude Code" line is fine.
