# Workflow opracowania rzutu

## Etap 1 — pozyskanie materiału
1. Wykonaj zdjęcie całego arkusza możliwie prostopadle, w dobrym świetle i bez cieni.
2. Zachowaj wszystkie krawędzie rzutu i widoczne wymiary.
3. Jeżeli dostępny jest skan, preferuj skan nad zdjęciem.
4. Nie przycinaj oryginału; kopię roboczą można prostować i kadrować.
5. Zapisz informację, czy obraz przedstawia cały rzut, czy fragment.

## Etap 2 — kalibracja
1. Wybierz odcinek o znanej długości, najlepiej długi i wyraźny.
2. Wskaż dwa końce odcinka w obrazie.
3. Wprowadź rzeczywistą długość w mm.
4. Sprawdź wynik na drugim znanym wymiarze, jeśli jest dostępny.
5. Jeśli skala różni się istotnie w różnych kierunkach, podejrzewaj perspektywę lub deformację; nie kompensuj tego arbitralnie.

Dla obrazu bez perspektywy: mm_per_pixel = known_length_mm / measured_length_pixels.

Preferowana ścieżka to panel wizualny:

```bash
floorplan-engine calibrate-ui --project plan.json --output plan.calibration.html
```

Otwórz plik HTML w przeglądarce, zaznacz punkty A i B, wpisz wymiar referencyjny i opcjonalnie ustaw punkt O. Pobierz skalibrowany JSON i umieść go obok oryginalnego projektu oraz obrazu, aby zachować działanie ścieżek względnych. Panel działa offline, ale nie koryguje perspektywy.

Przykładowa komenda, tworząca nowy plik projektu bez nadpisywania źródła:

```bash
floorplan-engine calibrate --project plan.json --first-pixel 120,400 --second-pixel 720,400 --length-mm 3000 --origin-pixel 120,400
```

W przypadku zdjęć z perspektywą pojedyncza skala może być niewystarczająca; potrzebna może być korekcja perspektywy na podstawie punktów odniesienia.

## Etap 3 — geometria architektoniczna
1. Wyznacz obrys, ściany, drzwi i okna.
2. Przypisz stabilne identyfikatory.
3. Zapisz pochodzenie geometrii: ręcznie określona, zmierzona lub automatycznie wykryta.
4. Oznacz niepewne fragmenty do potwierdzenia.
5. Porównaj odległości i wymiary modelu z wymiarami źródłowymi.

### Modelowanie ścian, drzwi, okien i pomieszczeń

- Każda ściana ma stabilne ID oraz odcinek od punktu początkowego do końcowego; opcjonalnie wpisz grubość w mm i rolę architektoniczną.
- Otwór musi wskazywać istniejącą ścianę przez `wall_id`. `offset_mm` jest odległością wzdłuż ściany od jej punktu startowego (nie od globalnego początku układu), a `width_mm` jest szerokością otworu.
- Nie umieszczaj otworu poza ścianą i nie nakładaj dwóch otworów na tym samym odcinku. Jeśli otwory są obok siebie, ich przedziały mogą stykać się końcami.
- Opisuj pomieszczenia przez wielokąt `vertices` w mm. Lista wierzchołków jest automatycznie zamykana, bez ponownego wpisywania pierwszego punktu na końcu. Wielokąt nie może przecinać samego siebie.
- Nazwa pomieszczenia jest wyświetlana w centroidzie pola. Dla pomieszczeń wklęsłych lub nieregularnych ustaw opcjonalne `label_position` ręcznie.
- Traktuj szkic PDF jako wizualną kontrolę modelu. Nie jest jeszcze automatycznym rozpoznaniem ani normowym symbolem CAD.

## Etap 4 — elementy elektryczne
1. Uzgodnij katalog symboli oraz ich znaczenie przed masowym rozmieszczaniem.
2. Rozmieszczaj symbole w układzie współrzędnych modelu, nie w pikselach obrazu.
3. Przechowuj typ, pozycję, obrót i identyfikator każdego symbolu.
4. Powiązania z obwodami dodawaj dopiero wtedy, gdy są znane i zweryfikowane.
5. Nie interpretuj niejednoznacznych oznaczeń bez oznaczenia ich jako niepotwierdzonych.

## Etap 5 — kontrola i PDF
Przed eksportem sprawdź:
- obecność kalibracji i jej poprawność;
- kompletność wymaganych metadanych;
- obiekty poza obrysem lub nieprawidłowe relacje;
- kolizje symboli i czytelność opisów;
- legendę, skalę, tytuł arkusza i orientację strony;
- listę ostrzeżeń i pozycji wymagających weryfikacji.

Uruchom kontrolę modelu i geometrii przed renderowaniem:

```bash
floorplan-engine check plan.calibrated.json --json
floorplan-engine plan.calibrated.json --output outputs/plan.pdf
```

Kontrola geometrii ostrzega o przecięciach wewnętrznych odcinków ścian, ich nakładaniu i niemal zbieżnych symbolach. Są to sygnały do przeglądu, nie automatyczne korekty geometrii. Wspólne końce i połączenia typu T są dozwolone.

Wygenerowany PDF należy obejrzeć w powiększeniu i wydrukować kontrolnie przed wykorzystaniem jako dokumentacji wykonawczej.

## Minimalny pakiet przekazywany do opracowania
- oryginalne zdjęcie/skan;
- co najmniej jeden wymiar referencyjny;
- informacja o jednostkach i ewentualnej skali wydruku;
- oczekiwane oznaczenia elektryczne lub legenda ze źródłowego projektu;
- informacja, czy plan ma przedstawiać istniejącą instalację, projektowaną instalację czy oba zakresy.

## Ograniczenia obecnego prototypu
Panel kalibracji wizualnej pozwala wybrać punkty myszą lub dotykiem, lecz nie wykonuje automatycznego wykrywania ścian ani korekcji perspektywy; nie ma też zatwierdzonego katalogu symboli zgodnego z konkretnym standardem. PDF jest dopasowywany do A4 poziomo, a nie do gwarantowanej skali wydruku 1:1.
