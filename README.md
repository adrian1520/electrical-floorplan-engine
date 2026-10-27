# Electrical Floorplan Engine

Narzędzie do przekształcania zdjęć lub skanów rzutów architektonicznych w uporządkowane plany instalacji elektrycznej, z eksportem do **PDF**.

## Status

**Etap: kalibracja CLI i diagnostyka geometrii.** Dostępne są modele danych, kalibracja skali obrazu, kontrola kolizji geometrii, renderowanie PDF z geometrią wektorową i skalibrowanym podkładem rastrowym oraz testy. Automatyczne rozpoznawanie ścian, korekcja perspektywy i docelowy katalog symboli pozostają kolejnymi etapami.

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

\`\`\`bash
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
pytest
\`\`\`

### Wygenerowanie demonstracyjnego PDF

\`\`\`bash
floorplan-engine examples/demo_project.json --output outputs/demo.pdf
\`\`\`

Przykładowy projekt zawiera wyłącznie syntetyczną geometrię. Nie jest projektem wykonawczym.

### Kalibracja obrazu

Przygotuj plik JSON z polem \`source_image\`, wskazującym ścieżkę do obrazu. Wskaż dwa punkty na odcinku o znanej długości (współrzędne pikselowe X,Y) i uruchom:

\`\`\`bash
floorplan-engine calibrate \\
  --project examples/my_plan.json \\
  --first-pixel 120,400 \\
  --second-pixel 720,400 \\
  --length-mm 3000
\`\`\`

Domyślnie punkt początku układu to \`--first-pixel\`. Można go nadpisać opcją \`--origin-pixel X,Y\`. Polecenie zapisuje osobny plik \`my_plan.calibrated.json\` i nie nadpisuje wejścia. Wynik zawiera skalę \`image_mm_per_pixel\` oraz piksel odpowiadający punktowi (0,0) modelu. Współrzędne obrazu zaczynają się w lewym górnym rogu, z osią Y skierowaną w dół.

Przy zdjęciu z perspektywą jednolita skala może nie wystarczyć — najpierw należy wyprostować obraz. Kalibrację warto zweryfikować na drugim znanym wymiarze.

### Kontrola geometrii przed eksportem

\`\`\`bash
floorplan-engine check examples/demo_project.json
floorplan-engine check examples/demo_project.json --json
\`\`\`

Kontrola raportuje przecięcia wewnętrzne ścian, nakładające się odcinki i symbole umieszczone w niemal identycznym miejscu. Połączenia ścian przez wspólne końce i połączenia typu T nie są zgłaszane. Są to ostrzeżenia do przeglądu — nie wszystkie przecięcia muszą być błędami projektowymi. Flaga \`--strict\` zwraca kod 1, gdy znaleziono ostrzeżenia; błędy danych wejściowych zwracają kod 2.

### Podkład rastrowy

Plik JSON projektu może zawierać \`source_image\`, \`image_mm_per_pixel\`, \`image_origin_pixel_x\` i \`image_origin_pixel_y\`. Ścieżki względne są interpretowane względem pliku JSON projektu podczas renderowania.

Renderer dopasowuje rysunek do A4 poziomo. Wynik nie jest gwarantowanym wydrukiem 1:1; dokładny wydruk w określonej skali będzie osobnym, testowanym etapem.

## Dokumentacja

- [Instrukcje dla agentów i współtwórców](AGENTS.md)
- [Architektura](docs/ARCHITECTURE.md)
- [Workflow opracowania rzutu](docs/WORKFLOW.md)
- [Decyzje techniczne](docs/DECISIONS.md)
