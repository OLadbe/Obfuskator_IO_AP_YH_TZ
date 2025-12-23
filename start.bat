@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 > nul

:: ==========================================================
:: AKTYWACJA ŚRODOWISKA VENV (jeśli istnieje)
:: ==========================================================
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
)

:: ==========================================================
:: KONFIGURACJA
:: ==========================================================
:: Główny plik źródłowy testowany przez obfuskator
set "SRC=hello.py"

:: Plik obfuskowany (obfuskator tworzy *_obf.py)
set "OBF=%SRC:.py=_obf.py%"

:: Skrypt obfuskatora
set "OBF_SCRIPT=obfuscator_viewable.py"

:: Skrypty deobfuskatora (4 kroki)
set "STEP1_SCRIPT=deobfuscator_step1_strings.py"
set "STEP2_SCRIPT=deobfuscator_step2_cleanup_strings_bootstrap.py"
set "STEP3_SCRIPT=deobfuscator_step3_restore_builtins.py"
set "STEP4_SCRIPT=deobfuscator_step4_rename_locals.py"

:: ==========================================================
:: SPRAWDZENIE, CZY PYTHON JEST DOSTĘPNY
:: ==========================================================
python -X utf8 --version >nul 2>nul
if errorlevel 1 (
    cls
    echo =====================================================
    echo  BLAD: Nie znaleziono Pythona
    echo =====================================================
    echo Upewnij sie, ze Python jest zainstalowany i dodany do PATH.
    echo https://www.python.org/
    echo.
    pause
    goto :eof
)

:: ==========================================================
:: MENU GŁÓWNE
:: ==========================================================
:menu
cls
echo ==========================================
echo        Obfuscator / Deobfuscator
echo ==========================================
echo Projekt: Low_obfuscator
echo Plik zrodlowy:        %SRC%
echo Plik obfuskowany:     %OBF%
echo.
echo 1. Obfuskuj "%SRC%" i URUCHOM "%OBF%"
echo 2. Obfuskuj "%SRC%" i WYSWIETL "%OBF%"
echo 3. DEOBFUSKUJ "%OBF%" (4 kroki) i WYSWIETL FINALNY KOD
echo 4. Wyjscie
echo.
choice /c 1234 /n /m "Wybierz opcje (1-4): "
if errorlevel 4 goto exit
if errorlevel 3 goto do_defuscate
if errorlevel 2 goto obfuscate_show
if errorlevel 1 goto obfuscate_run

:: ==========================================================
:: 1) Obfuskacja i uruchomienie
:: ==========================================================
:obfuscate_run
cls
echo == OBFUSKACJA I URUCHOMIENIE ==
echo Uruchamiam: python "%OBF_SCRIPT%" "%SRC%"
echo.
python -X utf8 "%OBF_SCRIPT%" "%SRC%"
if errorlevel 1 (
    echo.
    echo BLAD: Obfuskator zakonczyl sie bledem.
    pause
    goto menu
)

if exist "%OBF%" (
    echo.
    echo Plik obfuskowany: "%OBF%"
    echo Uruchamiam...
    echo.
    python -X utf8 "%OBF%"
) else (
    echo.
    echo BLAD: Plik "%OBF%" nie zostal znaleziony po obfuskacji.
)

echo.
pause
goto menu

:: ==========================================================
:: 2) Obfuskacja i wyswietlenie pliku
:: ==========================================================
:obfuscate_show
cls
echo == OBFUSKACJA I PODGLAD ==
echo Uruchamiam: python "%OBF_SCRIPT%" "%SRC%"
echo.
python -X utf8 "%OBF_SCRIPT%" "%SRC%"
if errorlevel 1 (
    echo.
    echo BLAD: Obfuskator zakonczyl sie bledem.
    pause
    goto menu
)

if exist "%OBF%" (
    echo.
    echo Plik obfuskowany: "%OBF%"
    echo ------------------------------------------
    type "%OBF%"
    echo ------------------------------------------
) else (
    echo.
    echo BLAD: Plik "%OBF%" nie zostal znaleziony po obfuskacji.
)

echo.
pause
goto menu

:: ==========================================================
:: 3) Deobfuskacja: 4 kroki pipeline
:: ==========================================================
:do_defuscate
cls
echo == DEOBFUSKACJA (4 KROKI) ==
echo.

if not exist "%OBF%" (
    echo BLAD: Plik obfuskowany "%OBF%" nie istnieje.
    echo Najpierw wykonaj obfuskacje ^(opcja 1 lub 2^).
    echo.
    pause
    goto menu
)

echo [KROK 1] Dekodowanie stringow (_s("BASE64"))
python -X utf8 "%STEP1_SCRIPT%" "%OBF%"
if errorlevel 1 (
    echo.
    echo BLAD w kroku 1.
    pause
    goto menu
)
set "DEOBF1=hello_d1.py"
if not exist "%DEOBF1%" (
    echo.
    echo BLAD: Nie znaleziono "%DEOBF1%".
    pause
    goto menu
)

echo [KROK 2] Czyszczenie bootstrapu (_s, import base64)
python -X utf8 "%STEP2_SCRIPT%" "%DEOBF1%"
if errorlevel 1 (
    echo.
    echo BLAD w kroku 2.
    pause
    goto menu
)
set "DEOBF2=hello_d2.py"
if not exist "%DEOBF2%" (
    echo.
    echo BLAD: Nie znaleziono "%DEOBF2%".
    pause
    goto menu
)

echo [KROK 3] Przywracanie wbudowanych funkcji (print/range/len/...)
python -X utf8 "%STEP3_SCRIPT%" "%DEOBF2%"
if errorlevel 1 (
    echo.
    echo BLAD w kroku 3.
    pause
    goto menu
)
set "DEOBF3=hello_d3.py"
if not exist "%DEOBF3%" (
    echo.
    echo BLAD: Nie znaleziono "%DEOBF3%".
    pause
    goto menu
)

echo [KROK 4] Uczytelnianie nazw lokalnych (_vXXXXXXXX -> var_1/func_1/...)
python -X utf8 "%STEP4_SCRIPT%" "%DEOBF3%"
if errorlevel 1 (
    echo.
    echo BLAD w kroku 4.
    pause
    goto menu
)
set "DEOBF4=hello_deobf.py"
if not exist "%DEOBF4%" (
    echo.
    echo BLAD: Nie znaleziono "%DEOBF4%".
    pause
    goto menu
)

echo.
echo ====================================================
echo  DEOBFUSKACJA ZAKONCZONA
echo  Finalny plik: "%DEOBF4%"
echo ====================================================
echo.
echo PODGLAD ZAWARTOSCI:
echo ------------------------------------------
type "%DEOBF4%"
echo ------------------------------------------
echo.
pause
goto menu

:: ==========================================================
:: 4) Wyjscie
:: ==========================================================
:exit
cls
echo Zamykam...
echo.
pause
endlocal
goto :eof
