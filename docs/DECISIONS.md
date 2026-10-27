# Rejestr decyzji technicznych

## ADR-001 — jednostki modelu
**Status:** przyjęta.

Wszystkie współrzędne i wymiary w modelu domenowym są przechowywane w milimetrach. Przeliczenia na jednostki renderera odbywają się na granicy eksportu. Powód: jednoznaczna geometria i ograniczenie błędów jednostek.

## ADR-002 — PDF jako pierwszy format wyjściowy
**Status:** przyjęta.

Pierwszym celem eksportu jest PDF. DXF/SVG nie należą do zakresu MVP, dopóki nie zostaną jawnie zatwierdzone. PDF powinien preferować wektorowe prymitywy i zachowywać czytelność przy wydruku.

## ADR-003 — deterministyczny silnik poza LLM
**Status:** przyjęta.

LLM może pomagać w interpretacji poleceń, proponowaniu zmian i wyjaśnianiu ostrzeżeń, ale trwały model danych, geometria, walidacja i generowanie dokumentu są realizowane przez jawny kod. Wynik nie może zależeć od swobodnej interpretacji promptu.

## ADR-004 — brak cichego zgadywania
**Status:** przyjęta.

Wymiary i geometria o nieznanym pochodzeniu są oznaczane jako niepotwierdzone. System ma zgłaszać braki i sprzeczności zamiast automatycznie przedstawiać je jako fakty.

## ADR-005 — sandbox jako środowisko prototypowania
**Status:** przyjęta z ograniczeniem.

Sandbox ChatGPT jest wybranym środowiskiem do uruchamiania prototypów i testów, w granicach dostępnych narzędzi. Nie jest traktowany jako trwały serwer aplikacyjny ani jako automatycznie połączony checkout repozytorium. GitHub pozostaje trwałym źródłem kodu i dokumentacji.
