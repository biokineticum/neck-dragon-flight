# Dragon Flight: High-Mountain Realm

[English version](README.en.md)

Gra o spokojnym locie smokiem nad górską krainą. Można sterować klawiaturą
i myszą albo ruchami głowy śledzonymi przez kamerę internetową. Projekt łączy
grę w Godot z modułem śledzenia twarzy napisanym w Pythonie.

## Rozgrywka

Świat obejmuje dolinę, góry, lasy, jezioro, rzekę i wodospad, a także osady,
zwierzęta i stada ptaków. W czasie lotu zmienia się pogoda, a otoczeniu
towarzyszą dźwięki przyrody. Lot jest bezpieczny: zderzenie z terenem nie
odbiera zdrowia ani nie kończy gry.

W powietrzu znajdują się serca rozmieszczone w różnych kierunkach. Aby je
zebrać, trzeba przez nie przelecieć. Po każdych pięciu sercach pojawiają się
fajerwerki i można kontynuować zbieranie. Licznik jest widoczny na ekranie.

## Wymagania

- Windows 10 lub 11 dla dołączonego programu uruchamiającego.
- Godot 4.7.2, dostępny jako polecenie `godot` lub wskazany przez `GODOT_BIN`.
- Python 3.11 oraz zależności z `tracker\requirements.txt` do śledzenia głowy.
- Kamera internetowa i zgoda systemu na jej używanie, jeśli sterujesz głową.

Kamera i Python nie są potrzebne do gry sterowanej klawiaturą i myszą
uruchomionej bezpośrednio w Godot.

## Uruchomienie

### Gra ze śledzeniem głowy

1. Zainstaluj Godot i Python oraz dodaj je do zmiennej systemowej `PATH`.
2. W katalogu projektu zainstaluj zależności:

   ```cmd
   python -m pip install -r tracker\requirements.txt
   ```

3. Uruchom `run_game.bat`. Program uruchomi tracker i grę, a po zamknięciu
   gry zakończy działanie trackera. Jeśli zależności nie są dostępne, launcher
   spróbuje je zainstalować.
4. Usiądź przed kamerą i rozpocznij lot przyciskiem na ekranie startowym albo
   klawiszem `Spacja` lub `Enter`. Naciśnij `C`, aby skalibrować pozycję głowy.

Jeśli Godot nie jest dostępny w `PATH`, wskaż jego plik i uruchom launcher
w tym samym oknie wiersza polecenia:

```cmd
set "GODOT_BIN=C:\Tools\Godot\Godot_v4.7.2-stable_win64_console.exe"
run_game.bat
```

Ścieżkę należy dostosować do miejsca instalacji Godot.

### Gra bez kamery

W katalogu projektu uruchom:

```cmd
godot --path .
```

Można też zaimportować `project.godot` w menedżerze projektów Godot
i uruchomić scenę główną.

### Uruchomienie trackera osobno

W osobnych terminalach uruchom:

```cmd
python tracker\head_tracker.py
```

```cmd
godot --path .
```

## Sterowanie

| Sterowanie | Działanie |
| --- | --- |
| `W` lub strzałka w górę | Wznoszenie |
| `S` lub strzałka w dół | Nurkowanie |
| `A` lub strzałka w lewo | Skręt w lewo |
| `D` lub strzałka w prawo | Skręt w prawo |
| `Q` lub lewy przycisk myszy | Przechylenie w lewo |
| `E` lub prawy przycisk myszy | Przechylenie w prawo |
| `C` | Kalibracja neutralnej pozycji głowy |
| `O` | Otwarcie lub zamknięcie ustawień |
| `R` | Ponowne rozpoczęcie lotu i wyzerowanie licznika serc |

Ruch głowy steruje wznoszeniem, skrętem i przechyleniem. Użycie klawiatury
lub przycisków myszy tymczasowo przejmuje sterowanie; po ich zwolnieniu gra
płynnie wraca do kamery, jeśli śledzenie jest aktywne. Czułość i odwrócenie
osi można zmienić w ustawieniach gry.

## Kamera i konfiguracja

Tracker korzysta z OpenCV i MediaPipe do wykrywania twarzy i wyznaczania
orientacji głowy. Wysyła kąty oraz status śledzenia jako dane JSON przez UDP
na lokalny adres `127.0.0.1:42425`. Gra odbiera je w `InputManager.gd`;
po utracie sygnału dostępne pozostaje sterowanie ręczne.

Ustawienia trackera znajdują się w `tracker\tracker_config.json`. Pole
`camera_id` wybiera kamerę, a `preview` włącza lub wyłącza okno podglądu.
Zmiany w pliku należy wprowadzić przed uruchomieniem trackera.

Jeśli kamera nie działa:

1. Sprawdź, czy nie jest zasłonięta lub wyłączona fizycznym przyciskiem.
2. Zezwól aplikacjom komputerowym na dostęp do kamery w ustawieniach Windows
   i zamknij inne programy, które mogą jej używać.
3. Sprawdź komunikaty w oknie launchera i w razie potrzeby zmień `camera_id`.
4. Upewnij się, że twarz jest widoczna i dobrze oświetlona.

Status `KEYBOARD / MOUSE` oznacza sterowanie ręczne, a niekoniecznie awarię
kamery. W trybie ręcznym można rozpocząć lot bez oczekiwania na tracker.

## Struktura projektu

| Ścieżka | Zawartość |
| --- | --- |
| `project.godot` | Konfiguracja projektu i przypisania wejścia |
| `scenes\` | Scena główna, smok i interfejs |
| `scripts\` | Logika lotu, świata, sterowania, pogody i serc |
| `materials\` | Materiały, shadery i środowisko |
| `tracker\` | Śledzenie głowy, konfiguracja i testy Pythona |
| `test\` | Testy Godot uruchamiane bez interfejsu |
| `e2e_tests\` | Dodatkowe testy integracyjne |
| `run_game.bat` | Launcher gry i trackera dla Windows |

## Testy

Z katalogu projektu można uruchomić zestaw testów Godot:

```cmd
godot --headless --path . -s test\run_all_tests.gd
```

Testy trackera:

```cmd
python -m pytest tracker\tests -q
```

Więcej informacji znajduje się w [SETUP.md](SETUP.md) oraz
[INTEGRATION.md](INTEGRATION.md).
