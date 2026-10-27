# AGENTS.md — zasady pracy w repozytorium

## Cel
Budować powtarzalny silnik do opracowywania rzutów instalacji elektrycznej i generowania dokumentacji PDF. Priorytetem są poprawność geometrii, jawne założenia, testowalność i śledzenie niepewności.

## Zasady obowiązkowe
1. **Nie zgaduj wymiarów.** Każda skala musi pochodzić z jawnej kalibracji lub danych źródłowych. Niepewne dane oznacz jako wymagające potwierdzenia.
2. **Jednostki wewnętrzne: milimetry (mm).** Nie mieszaj jednostek w modelu. Konwersje wykonuj na granicach API i eksportu.
3. **Deterministyczna geometria.** Te same dane wejściowe i konfiguracja muszą dawać ten sam model i wynik. Algorytmy geometryczne nie mogą zależeć od odpowiedzi LLM.
4. **Waliduj dane na wejściu.** Błędne współrzędne, skala, identyfikatory lub odwołania muszą kończyć się czytelnym błędem.
5. **Testuj zachowanie.** Dodawaj testy dla geometrii, konwersji jednostek, walidacji i eksportu. Każda poprawka błędu powinna mieć test regresyjny.
6. **Bez cichych napraw.** Automatyczne korekty obrazu/geometrii muszą być jawne, konfigurowalne i raportowane.
7. **PDF to cel MVP.** Nie dodawaj eksportu DXF/SVG, dopóki nie zostanie jawnie zaplanowany.
8. **Oddziel warstwy.** Model domenowy nie powinien zależeć od biblioteki PDF ani od interfejsu ChatGPT.
9. **Bez twierdzeń o zgodności normowej bez podstaw.** Walidacje normowe muszą wskazywać konkretną regułę, źródło i zakres zastosowania. W przeciwnym razie opisuj je jako kontrole techniczne, nie certyfikację.
10. **Nie umieszczaj danych prywatnych.** Zdjęcia planów, adresy i dane osobowe nie trafiają do repozytorium bez wyraźnej potrzeby i zgody.

## Styl kodu
- Python 3.11+; typowanie dla publicznych funkcji i modeli.
- Docstringi dla publicznych modułów/funkcji.
- Małe moduły o pojedynczej odpowiedzialności.
- Używaj pathlib do ścieżek i logging zamiast print w kodzie bibliotecznym.
- Nie łap ogólnego Exception, jeśli można obsłużyć konkretny błąd.
- Zależności produkcyjne dodawaj tylko wtedy, gdy rozwiązują jasno określony problem.

## Przed zakończeniem zmiany
1. Uruchom pytest.
2. Uruchom ruff check . oraz ruff format --check ., jeśli narzędzia są dostępne.
3. Zaktualizuj dokumentację, jeżeli zmienia się workflow lub zachowanie użytkowe.
4. W podsumowaniu wskaż zmiany, testy oraz znane ograniczenia.
