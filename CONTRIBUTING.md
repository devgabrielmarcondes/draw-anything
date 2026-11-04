# Contributing

Thank you for your help. Read these rules before you open a pull request.

## Set up

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

Install `ffmpeg` for video export. On Windows, `cairosvg` also needs the Cairo library (for example, from GTK for Windows).

## Check your change

```bash
ruff check .
pytest -m "not slow"             # fast tests
pytest                           # all tests, with the benchmark regression
python scripts/package_skill.py  # builds dist/draw-anything.skill
```

## Rules

1. **Language.** Write all code, comments, docs and commit messages in US English. Follow ASD-STE100 (Simplified Technical English): short sentences, active voice, the imperative in instructions, one term for one concept.
2. **Keep SKILL.md small.** The model loads `skills/draw-anything/SKILL.md` into its context. Keep it at approximately 8 KB or less. Put details in `skills/draw-anything/references/`.
3. **Use the benchmark to change defaults.** Do not change a default value of an algorithm without benchmark evidence. Tune on the `train` split. Report the result on the `test` split. Add the before and after numbers to the pull request.
4. **Use only free images.** Do not add images that have copyright protection. Use images that code makes, or images in the public domain. Give credit for public-domain works in `assets/README.md`.
5. **Make small commits.** Each commit does one thing. Write the subject line in the imperative ("Add ...", "Fix ...").
6. **Update the changelog.** Add each fix or feature to `CHANGELOG.md` under `[Unreleased]`.
