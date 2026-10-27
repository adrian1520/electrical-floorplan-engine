# CI i kontrola jakości

## Co sprawdza pipeline

Workflow `.github/workflows/tests.yml` uruchamia się przy pushu na `main`, dla pull requestów kierowanych do `main` oraz ręcznie przez GitHub Actions.

- Testy są wykonywane na Pythonie 3.11, 3.12, 3.13 i 3.14. Pokrywa to wersje używane obecnie w CI w obrębie zadeklarowanego minimum `requires-python = ">=3.11"`.
- Osobny job sprawdza `ruff check .` oraz `ruff format --check .`. Kontrole stylu są wykonywane tylko raz, a nie ponownie w każdym zadaniu macierzy.
- Uprawnienia workflow są ograniczone do odczytu zawartości repozytorium.
- Nowszy push lub aktualizacja tego samego pull requestu anuluje starszy, nieaktualny run. Pozwala to ograniczyć kolejkę i nie raportować jako bieżącego wyniku testów dla starszego commitu.
- Akcje `actions/checkout@v7` i `actions/setup-python@v7` zastępują wcześniejsze wersje korzystające z przestarzałego runtime'u Node.js 20.

## Lokalne odtworzenie kontroli

W środowisku z Pythonem 3.11 lub nowszym:

```bash
python -m pip install -e ".[dev,server]"
pytest
ruff check .
ruff format --check .
```

Każdy błąd walidacji lub testu powinien być naprawiony przy źródle i zabezpieczony testem regresyjnym, jeśli dotyczy zachowania aplikacji. Nie należy wyłączać reguł lintowania globalnie w celu ukrycia pojedynczego problemu formatowania; wyjątki powinny być ograniczone do pliku i uzasadnione.

## Testy backendu edytora

Zestaw deweloperski instaluje także dodatek serwerowy i HTTPX, aby testować API przez klienta ASGI. CI sprawdza listowanie projektów, dostarczanie rastra, zapis po walidacji, konflikty rewizji, wymagane nagłówki oraz odmowę dostępu do obrazów poza workspace. Samo przejście testów API nie zastępuje ręcznej kontroli użyteczności w przeglądarce.

## Wyniki audytu historii runów — 27 października 2026

W runach `#1–#48` odnotowano 44 niepowodzenia i 4 sukcesy. Większość awarii pojawiała się w trakcie sekwencyjnego wprowadzania zmian na `main` i kończyła się na lintowaniu lub formatowaniu, zanim pipeline został uruchomiony ponownie dla poprawionego commitu. W logach znaleziono m.in.:

- `UP037` — niepotrzebne cudzysłowy w adnotacjach typów;
- `I001` — formatowanie importów; dla modułu `calibration_ui.py` dodano wąski wyjątek, ponieważ osadzony szablon HTML zaczyna się po stałej łańcuchowej i reguła daje tu fałszywy alarm;
- `E501` — długie linie w osadzonym HTML/CSS/JavaScript; wyjątek dotyczy tylko `calibration_ui.py`;
- `B905` — brak jawnego parametru `strict` przy `zip()`;
- różnice formatowania Ruff, które były naprawiane przez formatowanie plików.

Dwa historyczne runy wskazały dodatkowo błędy testów: testy CLI wywoływały funkcję wejściową niezgodnie z jej interfejsem, a test samoprzecinającego się obrysu pomieszczenia oczekiwał innego komunikatu walidacji. Te przypadki zostały poprawione w kolejnych commitach. Aktualny zestaw regresyjny obejmuje te obszary.

Run `#52` dla commitu `262707303c7095b6d0258f8e2d81efa814043283` zakończył się sukcesem: **29 testów przeszło**, `ruff check .` zgłosił „All checks passed!” i `ruff format --check .` przeszedł poprawnie. Kolejna zmiana workflow musi przejść nowo dodaną macierz przed uznaniem aktualizacji CI za zweryfikowaną.
