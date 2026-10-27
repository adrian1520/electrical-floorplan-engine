# Electrical Floorplan Engine

Narzędzie do przekształcania zdjęć lub skanów rzutów architektonicznych w uporządkowane plany instalacji elektrycznej, z eksportem do **PDF**.

## Status

**Etap: fundament projektu.** Repozytorium zawiera dokumentację i konfigurację bazową. Silnik geometrii, kalibracja skali, biblioteka symboli oraz eksport PDF zostaną dodane etapami i objęte testami.

## Założenia projektowe

- **PDF jest formatem wyjściowym MVP** — dokument wektorowy, przygotowany do czytelnego wydruku.
- Wszystkie współrzędne modelu są przechowywane w **milimetrach**; konwersja do punktów PDF następuje dopiero podczas eksportu.
- Geometria, transformacje, walidacja i eksport muszą być deterministyczne i testowalne.
- Model danych i pliki projektu są źródłem prawdy. Rozmowa z modelem językowym nie zastępuje trwałego modelu geometrycznego.
- Niepewne wymiary i nierozpoznane elementy są oznaczane do weryfikacji, a nie po cichu zgadywane.
- Wynik jest dokumentacją pomocniczą; wymaga przeglądu przez osobę kompetentną przed użyciem wykonawczym.

## Plan prac

1. Specyfikacja, architektura, workflow i konfiguracja testów.
2. Model danych w mm, walidacja i identyfikatory obiektów.
3. Import obrazu, kalibracja skali i kontrola jakości.
4. Reprezentacja ścian, otworów oraz symboli instalacji elektrycznej.
5. Generowanie PDF z legendą, skalą i metryką arkusza.
6. Testy regresyjne na kontrolnych rzutach i workflow dla zdjęć z iPhone'a.

## Szybki start

Wymagany Python: 3.11 lub nowszy. Utwórz środowisko wirtualne, zainstaluj pakiet wraz z zależnościami deweloperskimi i uruchom testy:

- macOS/Linux: python -m venv .venv
- macOS/Linux: source .venv/bin/activate
- Windows PowerShell: .venv\\Scripts\\Activate.ps1
- Instalacja: python -m pip install -e ".[dev]"
- Testy: pytest

Na etapie fundamentu nie ma jeszcze polecenia generującego PDF. Zostanie dodane wraz z pierwszym pionowym przekrojem funkcjonalnym.

## Dokumentacja

- [Instrukcje dla agentów i współtwórców](AGENTS.md)
- [Architektura](docs/ARCHITECTURE.md)
- [Workflow opracowania rzutu](docs/WORKFLOW.md)
- [Decyzje techniczne](docs/DECISIONS.md)
