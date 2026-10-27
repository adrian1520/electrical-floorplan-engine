# Electrical Floorplan Engine

Narzędzie do przekształcania zdjęć lub skanów rzutów architektonicznych w uporządkowane plany instalacji elektrycznej, z eksportem do **PDF**.

## Status

**Etap: pierwszy pionowy przekrój funkcjonalny.** Dostępne są modele danych, kalibracja skali obrazu, renderowanie PDF z geometrią wektorową i skalibrowanym podkładem rastrowym, CLI oraz testy. Automatyczne rozpoznawanie ścian i docelowy katalog symboli są kolejnymi etapami.

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
source .venv/bin/activate  # Windows PowerShell: .venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
pytest
```

### Wygenerowanie demonstracyjnego PDF

```bash
floorplan-engine examples/demo_project.json --output outputs/demo.pdf
```

Przykładowy projekt zawiera wyłącznie syntetyczną geometrię. Nie jest projektem wykonawczym.

### Podkład rastrowy i kalibracja

Plik JSON projektu może zawierać:
- `source_image`: ścieżkę do lokalnego obrazu;
- `image_mm_per_pixel`: skalę kalibracji w mm/piksel;
- `image_origin_pixel_x` i `image_origin_pixel_y`: współrzędne piksela odpowiadającego punktowi (0, 0) modelu.

Kalibrację można obliczyć przez `ScaleCalibration` z modułu `electrical_floorplan_engine.calibration`. Punkty obrazu mają początek w lewym górnym rogu i oś Y skierowaną w dół; model ma oś Y skierowaną w górę. Przy zdjęciu z perspektywą jednolita skala może nie wystarczyć — najpierw należy wyprostować obraz.

Przykład projektu z podkładem wymaga podania skali i punktu początku układu. Renderer dopasowuje całość do A4 poziomo, dlatego wynik nie jest gwarantowanym wydrukiem 1:1.

## Dokumentacja

- [Instrukcje dla agentów i współtwórców](AGENTS.md)
- [Architektura](docs/ARCHITECTURE.md)
- [Workflow opracowania rzutu](docs/WORKFLOW.md)
- [Decyzje techniczne](docs/DECISIONS.md)
