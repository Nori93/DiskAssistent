# Contributing to DiskAssistent

## Branches

| Branch | Przeznaczenie |
|--------|---------------|
| `main` | Stabilne wydania (production-ready) |
| `develop` | Główna gałąź development — baza dla nowych PR |
| `feature/<nazwa>` | Nowa funkcjonalność |
| `fix/<nazwa>` | Naprawa błędu |
| `release/<version>` | Przygotowanie wydania (np. `release/1.1.0`) |
| `hotfix/<nazwa>` | Pilna naprawa błędu na `main` |

Nowe gałęzie zawsze tworzyć od `develop`:

```bash
git checkout develop
git pull
git checkout -b feature/moja-funkcja
```

---

## Commit messages

Format: **Conventional Commits**

```
<typ>(<zakres>): <opis>

[opcjonalne ciało]

[opcjonalne stopki, np. Closes #12]
```

### Typy

| Typ | Kiedy używać |
|-----|-------------|
| `feat` | Nowa funkcjonalność |
| `fix` | Naprawa błędu |
| `docs` | Zmiany w dokumentacji |
| `refactor` | Refaktoryzacja bez zmiany zachowania |
| `test` | Dodanie lub poprawienie testów |
| `chore` | Zmiany w konfiguracji, buildzie, CI |
| `perf` | Poprawa wydajności |

### Przykłady

```
feat(scan): add batch upsert to _run_scan
fix(app.js): pass currentCategory to loadCategoryGroups on cleanup
docs(readme): add architecture diagram
chore: add pre-commit ruff hook
```

---

## Pull Requests

1. Branch zawsze w kierunku `develop` (nie `main`)
2. Tytuł PR = ten sam format co commit message
3. Powiąż PR z Issue: `Closes #<numer>` w opisie
4. PR musi przejść wszystkie checks (CI) zanim zostanie zmergowany
5. Squash merge lub rebase — brak merge commits na `develop`

---

## Kod

- Python: formatowanie `black`, linting `ruff`
- Maksymalna długość linii: **100 znaków**
- Bez `print()` w kodzie produkcyjnym — używaj `logging`
- Nowe endpointy muszą mieć odpowiadający test integracyjny

---

## Wydania (Release)

```bash
git checkout -b release/X.Y.Z develop
# bump version w config.py (APP_VERSION)
git commit -m "chore: bump version to X.Y.Z"
git checkout main
git merge release/X.Y.Z --no-ff
git tag vX.Y.Z
git push origin main --tags
git checkout develop
git merge release/X.Y.Z --no-ff
git push origin develop
```
