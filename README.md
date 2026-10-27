# Electrical Floorplan Engine

Narzędzie do przekształcania zdjęć lub skanów rzutów architektonicznych w uporządkowane plany instalacji elektrycznej, z eksportem do **PDF**.

## Status

**Etap: model architektoniczny, kalibracja wizualna i edytor geometrii.** Dostępne są ściany z metadanymi, otwory drzwiowe/okienne przypisane do ścian, pomieszczenia z walidowanymi obrysami, kontrola geometrii i PDF z etykietami pomieszczeń oraz schematycznie renderowanymi otworami. Automatyczne rozpoznawanie ścian i korekcja perspektywy pozostają kolejnymi etapami.

## Założenia projektowe

- **PDF jest formatem wyjściowym MVP** — dokument wektorowy, przygotowany do czytelnego wydruku.
- Wszystkie współrzędne modelu są przechowywane w **milimetrach**.
- Geometria, transformacje, walidacja i eksport są deterministyczne i testowalne.
- Model danych i pliki projektu są źródłem prawdy; rozmowa z modelem językowym nie zastępuje trwałego modelu geometrycznego.
- Niepewne wymiary i nierozpoznane elementy są oznaczane do weryfikacji, a nie po cichu zgadywane.
- PDF jest obecnie **dopasowywany do arkusza**. Nie gwarantuje skali wydruku 1:1; nie należy mierzyć wymiarów na wydruku.
- Symbole w obecnym MVP są schematyczne i wymagają uzgodnienia z docelową legendą.

## Szybki start

Wymagany Python: 3.11 lub nowszy.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev,server]"
pytest
```

### Wygenerowanie demonstracyjnego PDF

```bash
floorplan-engine examples/demo_project.json --output outputs/demo.pdf
```

Przykładowy projekt zawiera wyłącznie syntetyczną geometrię. Nie jest projektem wykonawczym.

### Kalibracja obrazu

Przygotuj plik JSON z polem `source_image`, wskazującym ścieżkę do obrazu. Wskaż dwa punkty na odcinku o znanej długości (współrzędne pikselowe X,Y) i uruchom:

```bash
floorplan-engine calibrate --project examples/my_plan.json --first-pixel 120,400 --second-pixel 720,400 --length-mm 3000
```

Domyślnie punkt początku układu to `--first-pixel`. Można go nadpisać opcją `--origin-pixel X,Y`. Polecenie zapisuje osobny plik `my_plan.calibrated.json` i nie nadpisuje wejścia. Wynik zawiera skalę `image_mm_per_pixel` oraz piksel odpowiadający punktowi (0,0) modelu. Współrzędne obrazu zaczynają się w lewym górnym rogu, z osią Y skierowaną w dół.

Przy zdjęciu z perspektywą jednolita skala może nie wystarczyć — najpierw należy wyprostować obraz. Kalibrację warto zweryfikować na drugim znanym wymiarze.

### Wizualna kalibracja punktami

Zamiast ręcznie odczytywać współrzędne pikselowe, wygeneruj panel HTML. Obraz zostanie osadzony w pliku, więc panel działa lokalnie w przeglądarce i nie potrzebuje serwera ani połączenia sieciowego.

```bash
floorplan-engine calibrate-ui --project my_plan.json --output my_plan.calibration.html
```

Otwórz utworzony plik HTML w przeglądarce. Wskaż punkty A i B na znanym wymiarze, wpisz jego długość w mm, a następnie — opcjonalnie — wskaż punkt O początku układu. Dostępne są powiększenie, pomniejszenie i dopasowanie obrazu do widoku. Przycisk eksportu pobierze skalibrowany JSON.

Zapisz pobrany JSON obok oryginalnego pliku projektu i obrazu, aby względna ścieżka `source_image` nadal była prawidłowa. Sprawdź skalę na drugim znanym wymiarze. Panel przyjmuje jednolitą skalę i nie prostuje zdjęć z perspektywą; nie traktuj go jako automatycznej rekonstrukcji rzutu.

### Edytor geometrii w trybie backendowym

Do regularnej pracy uruchom backend w oddzielnym katalogu roboczym. Skopiuj tam skalibrowany JSON oraz obraz źródłowy (ścieżka **source_image** musi wskazywać plik wewnątrz workspace). Zainstaluj dodatek serwerowy przez **python -m pip install -e ".[server]"**, a następnie uruchom:

~~~bash
floorplan-engine server --workspace ./workspace --host 127.0.0.1 --port 8765
~~~

Otwórz http://127.0.0.1:8765, wybierz projekt i pracuj w przeglądarce. Obraz jest dostarczany przez API, a przycisk „Waliduj i zapisz na backendzie” wysyła geometrię do serwera. Backend waliduje model Pydantic i zapisuje plik JSON w katalogu workspace; nie tworzy dodatkowego pliku eksportowego. „Pobierz kopię JSON” pozostaje dostępne jako ręczny eksport. Schemat API znajduje się pod http://127.0.0.1:8765/docs.

Zapisy są atomowe i chronione nagłówkiem **If-Match** z rewizją SHA-256. Jeśli plik zmieni się po otwarciu edytora, backend odrzuci zapis kodem HTTP 409 — odśwież stronę, aby wczytać bieżącą wersję. Backend domyślnie nasłuchuje wyłącznie na localhost i nie ma uwierzytelniania; nie wystawiaj go do sieci bez dodatkowej warstwy bezpieczeństwa. Ścieżki obrazów muszą pozostać w katalogu workspace.

### Edytor offline

Tryb samodzielnego HTML pozostaje dostępny, gdy nie chcesz uruchamiać serwera:

~~~bash
floorplan-engine edit-geometry --project my_plan.calibrated.json --output my_plan.geometry.html
~~~

HTML osadza wtedy obraz oraz dane projektu, działa bez sieci, a „Waliduj i pobierz JSON” pobiera kopię pliku .geometry.json; nie zapisuje jej automatycznie do pliku źródłowego. Oba tryby obsługują ręczne rysowanie ścian, obrysów pomieszczeń i otworów, przeciąganie uchwytów, edycję właściwości, usuwanie i cofanie ostatnich zmian. Edytor nie rozpoznaje automatycznie ścian z pikseli ani nie koryguje perspektywy.

### Kontrola geometrii przed eksportem

```bash
floorplan-engine check examples/demo_project.json
floorplan-engine check examples/demo_project.json --json
```

Kontrola raportuje przecięcia wewnętrzne ścian, nakładające się odcinki i symbole umieszczone w niemal identycznym miejscu. Połączenia ścian przez wspólne końce i połączenia typu T nie są zgłaszane. Są to ostrzeżenia do przeglądu — nie wszystkie przecięcia muszą być błędami projektowymi. Flaga `--strict` zwraca kod 1, gdy znaleziono ostrzeżenia; błędy danych wejściowych zwracają kod 2.

### Model architektoniczny: ściany, otwory i pomieszczenia

Ściana jest odcinkiem w mm z opcjonalną grubością i rolą (`exterior`, `interior`, `partition`, `unknown`). Otwór odwołuje się do ściany przez `wall_id`; `offset_mm` mierzy odległość od początku odcinka ściany, a `width_mm` określa szerokość otworu. Otwory nie mogą wykraczać poza ścianę ani nakładać się na siebie na tej samej ścianie.

Pomieszczenie jest wielokątem z listą `vertices`; domknięcie obrysu jest domyślne (nie powtarzaj pierwszego wierzchołka na końcu). Walidacja odrzuca obrysy samoprzecinające się, zerowej powierzchni i z powtórzonymi wierzchołkami. Opcjonalne `label_position` pozwala ręcznie ustawić etykietę, gdy centroid wielokąta nie jest odpowiednim miejscem.

Przykładowy projekt obejmujący te obiekty znajduje się w `examples/demo_project.json`. PDF pokazuje przerwy w ścianach, symboliczny skrzydło drzwiowe, ramy okien i nazwy pomieszczeń. Reprezentacja pozostaje schematyczna; nie zastępuje zatwierdzonego rysunku architektonicznego.

### Podkład rastrowy

Plik JSON projektu może zawierać `source_image`, `image_mm_per_pixel`, `image_origin_pixel_x` i `image_origin_pixel_y`. Ścieżki względne są interpretowane względem pliku JSON projektu podczas renderowania.

Renderer dopasowuje rysunek do A4 poziomo. Wynik nie jest gwarantowanym wydrukiem 1:1; dokładny wydruk w określonej skali będzie osobnym, testowanym etapem.

## Dokumentacja

- [Instrukcje dla agentów i współtwórców](AGENTS.md)
- [Architektura](docs/ARCHITECTURE.md)
- [Workflow opracowania rzutu](docs/WORKFLOW.md)
- [Decyzje techniczne](docs/DECISIONS.md)
- [CI i kontrola jakości](docs/CI.md)
