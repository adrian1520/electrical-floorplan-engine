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

W przypadku zdjęć z perspektywą pojedyncza skala może być niewystarczająca; potrzebna może być korekcja perspektywy na podstawie punktów odniesienia.

## Etap 3 — geometria architektoniczna
1. Wyznacz obrys, ściany, drzwi i okna.
2. Przypisz stabilne identyfikatory.
3. Zapisz pochodzenie geometrii: ręcznie określona, zmierzona lub automatycznie wykryta.
4. Oznacz niepewne fragmenty do potwierdzenia.
5. Porównaj odległości i wymiary modelu z wymiarami źródłowymi.

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

Wygenerowany PDF należy obejrzeć w powiększeniu i wydrukować kontrolnie przed wykorzystaniem jako dokumentacji wykonawczej.

## Minimalny pakiet przekazywany do opracowania
- oryginalne zdjęcie/skan;
- co najmniej jeden wymiar referencyjny;
- informacja o jednostkach i ewentualnej skali wydruku;
- oczekiwane oznaczenia elektryczne lub legenda ze źródłowego projektu;
- informacja, czy plan ma przedstawiać istniejącą instalację, projektowaną instalację czy oba zakresy.
