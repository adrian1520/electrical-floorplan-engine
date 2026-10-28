# Beta sandbox ChatGPT — tryb bez integracji zewnętrznych

Repozytorium zawiera offline calibration editor, click-and-drag geometry editor, walidację geometrii i eksport PDF. Ten tryb jest podstawowym wariantem beta: bez serwera MCP, hostingu, tokenów, synchronizacji API i zdalnej bazy.

## Przepływ

1. Użytkownik dołącza PDF lub skan w bieżącej konwersacji.
2. Python/Data Analysis pracuje na kopii pliku w bieżącej sesji. Sprawdź rzeczywistą ścieżkę załącznika; nie zakładaj, że pliki z poprzedniej rozmowy nadal istnieją.
3. Przygotuj raster wybranej strony PDF, jeśli renderer jest już dostępny; w przeciwnym wypadku poproś o PNG/JPG.
4. Utwórz JSON projektu; kalibracja jest wymagana przed wymiarowaną geometrią.
5. Wygeneruj samodzielny HTML kalibratora, otwórz go lokalnie, kliknij dwa punkty o znanym wymiarze i pobierz skalibrowany JSON.
6. Wygeneruj HTML edytora geometrii, otwórz lokalnie, narysuj ściany/pomieszczenia/otwory i pobierz JSON.
7. Waliduj model i wygeneruj PDF/raport. Przekaż artefakty do rozmowy.
8. Zachowaj JSON i changelog, aby odtworzyć stan. To użytkownik wybiera, które pliki utrzymać między sesjami.

## Użycie helpera

Uruchom w checkoutcie repozytorium, gdy jego źródło i zależności są faktycznie obecne w sesji.

    from pathlib import Path
    import sys
    REPO_ROOT = Path("/actual/path/to/electrical-floorplan-engine")
    assert REPO_ROOT.exists()
    sys.path.insert(0, str(REPO_ROOT / "src"))
    sys.path.insert(0, str(REPO_ROOT / "sandbox_beta"))
    from floorplan_session import initialize_session, make_calibration_editor, make_geometry_editor, validate_and_export

Przygotowanie sesji z obrazu lub PDF.

    result = initialize_session(
        "/actual/path/to/scan.pdf", "/mnt/data/floorplan_beta",
        title="Rzut roboczy", pdf_page=1, dpi=200
    )
    result

Jeśli PDF wymaga PyMuPDF i biblioteka nie jest już zainstalowana, nie pobieraj jej z sieci: użyj istniejącego renderera lub poproś o PNG/JPG odpowiedniej strony.

Kalibracja.

    calibration_html = make_calibration_editor(result["project_json"])
    calibration_html

Edycja.

    geometry_html = make_geometry_editor(
        "/actual/path/to/project.calibrated.json"
    )
    geometry_html

Walidacja i PDF.

    report = validate_and_export(
        "/actual/path/to/project.geometry.json",
        "/mnt/data/floorplan_beta/floorplan.pdf",
        output_report_json="/mnt/data/floorplan_beta/validation.json"
    )
    report

Zastąp ścieżki rzeczywistymi nazwami wyników pobranych z HTML. Nie deklaruj gotowego PDF przed utworzeniem artefaktu.

## Model i zasady bezpieczeństwa

- Stan projektu jest JSON-em modelu FloorplanProject; współrzędne to mm, raster ma własną ścieżkę, skala i początek układu są jawne.
- sandbox_beta/floorplan_session.py udostępnia funkcje kalibracji, transformacji pikseli, dodawania ścian/pomieszczeń oraz operacje na plikach.
- Moduł nie uruchamia serwera i nie wykonuje zapytań sieciowych. Nie instaluje automatycznie zależności.
- Geometria jest ręczna. Brak automatycznej wektoryzacji i gwarancji zgodności z przepisami.
- GitHub jest kanonicznym źródłem kodu i testów, a nie automatycznie podłączonym dyskiem sesji Python. Użyj archiwum repozytorium albo faktycznie dostępnego źródła.
- Nie zapisuj skanów/PDF do GitHub domyślnie. Projekt JSON i walidację można zapisać jako zewnętrzną pamięć, jeśli użytkownik świadomie to zaakceptuje.
