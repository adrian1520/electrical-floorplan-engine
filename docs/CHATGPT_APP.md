# Edytor rzutu w rozmowie ChatGPT

## Co to jest

`chatgpt_mcp.py` udostępnia MCP App: narzędzie `open_floorplan_editor` zwraca UI resource (`ui://electrical-floorplan/geometry-editor-v1.html`) renderowany przez kompatybilnego klienta jako osadzony panel. Interfejs rozmawia z serwerem przez most MCP Apps (`ui/initialize`, `tools/call`), nie przez założony adres `localhost`.

Widżet w tym pierwszym przekroju obsługuje wybór projektu, podgląd podkładu, dodawanie ścian/pomieszczeń/otworów, cofanie, walidację i zapis. Geometria nadal jest ręcznie opracowywana; nie ma automatycznego wykrywania ścian ani korekcji perspektywy.

## Wymagania

- Python 3.11+ i opcjonalne zależności serwera (`python -m pip install -e ".[server]"`).
- Katalog workspace z skalibrowanymi plikami JSON i rastrami źródłowymi. Ścieżki obrazów muszą rozwiązywać się wewnątrz workspace.
- Działający endpoint MCP po HTTPS dostępny dla ChatGPT albo tunel Secure MCP Tunnel. ChatGPT nie łączy się bezpośrednio z serwerem osiągalnym wyłącznie z komputera użytkownika.
- Uprawnienia konta/workspace do dodawania własnych serwerów MCP. Obsługa interaktywnego UI oraz zapisów może zależeć od planu i ustawień administratora.

## Uruchomienie serwera

Przygotuj katalog roboczy z plikami JSON i obrazami:

~~~bash
python -m pip install -e ".[server]"
export ELECTRICAL_FLOORPLAN_WORKSPACE="./workspace"
export ELECTRICAL_FLOORPLAN_API_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export MCP_ALLOWED_HOSTS="mcp.twoja-domena.example"
export MCP_ALLOWED_ORIGINS="https://mcp.twoja-domena.example"
uvicorn electrical_floorplan_engine.chatgpt_mcp:app --host 0.0.0.0 --port 8000
~~~

Endpoint MCP jest dostępny pod `/mcp`. Podane wartości domeny są przykładami — zastąp je prawdziwą domeną hostingu/tunelu. Nie zapisuj tokenu w repozytorium ani w pliku, który będzie commitowany.

Middleware odmawia dostępu, gdy `ELECTRICAL_FLOORPLAN_API_TOKEN` nie jest ustawiony albo nagłówek `Authorization: Bearer <token>` nie zgadza się z konfiguracją. Skonfiguruj ten mechanizm uwierzytelnienia w połączeniu aplikacji ChatGPT, jeśli jest dostępny w wybranym przepływie. Nie usuwaj kontroli tokenu w celu przyspieszenia wdrożenia. Przy hostingu publicznym skonfiguruj również listy `MCP_ALLOWED_HOSTS` oraz `MCP_ALLOWED_ORIGINS`.

## Dodanie do ChatGPT

1. Upewnij się, że dany plan/workspace i jego administrator pozwalają dodawać własne serwery MCP z narzędziami zapisującymi.
2. W ChatGPT otwórz ustawienia aplikacji/wtyczek i wybierz utworzenie lub dodanie własnego serwera MCP.
3. Wprowadź publiczny adres HTTPS zakończony ścieżką `/mcp` (albo wybierz obsługiwany Secure MCP Tunnel).
4. Skonfiguruj uwierzytelnienie i zeskanuj narzędzia.
5. Otwórz nową rozmowę i wywołaj `open_floorplan_editor`. Widget pojawi się w obszarze rozmowy. Wybierz projekt z katalogu workspace.
6. Przetestuj najpierw na kopii projektu. Zapis aktualizuje plik JSON na backendzie; nie jest to jedynie eksport do pobrania.

Dokładne położenie ustawień zależy od wersji interfejsu i polityk konta. W aktualnym przepływie łączenie własnych serwerów MCP wymaga publicznego HTTPS lub tunelu, a prawa administratora i obsługa narzędzi zapisujących zależą od planu/workspace.

## Narzędzia MCP

- `open_floorplan_editor`: wyświetla interfejs i listę projektów.
- `list_floorplan_projects`: zwraca projekty oraz informację, czy nadają się do edycji.
- `load_floorplan_project`: zwraca model, rewizję SHA-256 i obraz w formie data URI; raster widżetu jest ograniczony do 12 MiB.
- `validate_floorplan_project`: waliduje model i raportuje ostrzeżenia geometrii bez zapisu.
- `save_floorplan_project`: waliduje i atomowo zapisuje JSON tylko wtedy, gdy rewizja wciąż jest zgodna; konflikt jest odrzucany.

## Bezpieczeństwo i ograniczenia

- Token jest wymagany; endpoint zwraca błąd, dopóki sekret nie zostanie skonfigurowany.
- Ścieżki projektu i rastra są ograniczone do katalogu workspace.
- Nie udostępniaj danych rzeczywistych, dopóki kontrola dostępu, kopie zapasowe i hosting nie są skonfigurowane.
- Ta integracja nie jest automatycznie wdrażana przez CI. Dodanie plików do GitHub nie tworzy zdalnego endpointu i samo nie dodaje aplikacji do ustawień ChatGPT.
- Dla części kont pełny zapis przez MCP może być niedostępny lub wymagać zatwierdzenia administratora. W takim przypadku pozostaje tryb offline `floorplan-engine edit-geometry`.
