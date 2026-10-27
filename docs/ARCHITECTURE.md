# Architektura

## Cel MVP
Przyjmować zdjęcie/skan rzutu, kalibrować obraz na podstawie znanego wymiaru, przechowywać geometrię w milimetrach i generować czytelny PDF z planem oraz symbolami instalacji elektrycznej.

## Przepływ danych
Zdjęcie/skan → import i kontrola jakości → kalibracja skali i transformacja obrazu → model projektu w mm → walidacja → renderer PDF → PDF i raport ostrzeżeń.

## Granice odpowiedzialności

### Warstwa wejścia obrazu
- Odczyt pliku i kontrola wymiarów/orientacji.
- Opcjonalne prostowanie perspektywy i poprawa kontrastu.
- Zachowanie oryginału; przetworzone obrazy są artefaktami pochodnymi.
- Każda transformacja obrazu musi być zapisana w metadanych.

### Kalibracja i geometria
- Jawny punkt odniesienia oraz znana długość w mm.
- Obliczenie skali i, gdy potrzebne, transformacji perspektywicznej.
- Geometria domenowa niezależna od rozdzielczości zdjęcia.
- Odróżnienie danych zmierzonych, wywnioskowanych i ręcznie wprowadzonych.

### Model domenowy
Docelowe encje:
- Project: metadane projektu, jednostki, arkusz i ustawienia eksportu.
- SourceImage: plik źródłowy, wymiary pikselowe i historia transformacji.
- Calibration: punkty/odcinek referencyjny, długość referencyjna i wynikowa skala.
- Room: pomieszczenie i etykieta.
- Wall / Opening: geometria ścian i otworów.
- ElectricalSymbol: typ symbolu, pozycja, obrót i właściwości.
- Circuit: obwód oraz relacje między elementami, jeśli znajdą się w zakresie.
- Issue: ostrzeżenie, błąd lub pozycja wymagająca decyzji użytkownika.

Każdy obiekt geometryczny powinien mieć stabilne ID. Niepewność nie może być kodowana wyłącznie w opisie tekstowym.

### Eksport PDF
- Renderer przyjmuje zwalidowany model, a nie surową rozmowę lub obraz.
- Rysunek powinien zawierać skalę, legendę symboli, tytuł/identyfikator arkusza i raport istotnych ostrzeżeń.
- Geometria ma być renderowana wektorowo tam, gdzie to możliwe.
- Ustawienia arkusza, marginesy, skala wydruku i grubości linii muszą być jawne.
- Raport powinien ujawniać elementy niepotwierdzone i niekompletne.

## Proponowany układ pakietu
- src/electrical_floorplan_engine/cli.py — interfejs wiersza poleceń
- src/electrical_floorplan_engine/config.py — konfiguracja i ustawienia arkusza
- src/electrical_floorplan_engine/models/ — modele domenowe i walidacja
- src/electrical_floorplan_engine/image/ — import, preprocessing, kalibracja
- src/electrical_floorplan_engine/geometry/ — transformacje i operacje geometryczne
- src/electrical_floorplan_engine/symbols/ — katalog i rozmieszczenie symboli
- src/electrical_floorplan_engine/rendering/ — renderer PDF
- src/electrical_floorplan_engine/reporting/ — ostrzeżenia i raport kontroli
- tests/ — testy jednostkowe i integracyjne
- docs/ — dokumentacja

Katalogi będą tworzone w momencie implementacji danego modułu; nie tworzymy pustych pakietów bez potrzeby.

## Środowisko wykonawcze
Python uruchamiany w dostępnym sandboxie ChatGPT może służyć do prototypowania i testowania, ale jego pliki tymczasowe nie są źródłem trwałości. Kod i dokumentacja są przechowywane w GitHub. Nie zakładaj, że sandbox automatycznie ma dostęp do repozytorium lub że sesja zachowa stan. Integrację należy jawnie wykonać przez pobranie repozytorium albo przez skonfigurowany konektor.

## Kryteria gotowości PDF
- Model wejściowy przeszedł walidację.
- Skala jest jawna i dodatnia.
- Jednostki oraz orientacja arkusza są określone.
- Elementy krytyczne lub niepewne są pokazane w raporcie.
- Test integracyjny sprawdza, że PDF powstaje i zawiera oczekiwane strony/elementy.


## Stan implementacji pierwszego przekroju

Dostępne moduły:
- `models.py`: zwalidowane punkty, odcinki, symbole i projekt w mm;
- `calibration.py`: jednolita kalibracja piksel → mm z jawnym punktem początku układu;
- `rendering/pdf.py`: jednostronicowy PDF A4 poziomo, podkład rastrowy i geometria wektorowa;
- `cli.py`: walidacja JSON i uruchomienie renderera.

Ograniczenia bieżącej wersji:
- nie ma automatycznego wykrywania ścian z obrazu;
- kalibracja jest jednolita i nie koryguje perspektywy;
- PDF jest dopasowywany do arkusza, a nie drukowany w gwarantowanej skali 1:1;
- symbole są schematycznymi znacznikami, a nie zatwierdzoną biblioteką normową.
