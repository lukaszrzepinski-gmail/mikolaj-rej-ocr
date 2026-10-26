# Lokalna aplikacja webowa i pipeline

Zakres: galeria lokalnych skanów, zaznaczanie i obrót, segmentacja linii bazowych, układ auto/jedna/dwie kolumny, kolejność czytania, cache geometrii, OCR wierszy, opcjonalny Diariusz LM, historia wariantów, porównanie RAW/LM i modeli, interaktywny raport skan ↔ tekst oraz ręczne poprawki wierszy. Skany są przetwarzane na komputerze użytkownika. Serwer słucha wyłącznie na 127.0.0.1. Jest narzędziem dla jednej lokalnej sesji, nie usługą wieloużytkownikową do Internetu.

## Instalacja — Windows, Python 3.12

Z katalogu repozytorium kodu:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install torch==2.10.0 torchvision==0.25.0 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
```

Lista przypina bezpośrednie wersje, nie wszystkie zależności przechodnie. Nie wykonano nowej instalacji podczas przygotowania publikacji. Pełna aplikacja zachowuje kontrolę pamięci i priorytetu Windows. Linux/macOS nie są tu deklarowane jako sprawdzone platformy pełnego GUI; osobny wrapper PAGE opisuje LOCAL_INFERENCE.md.

Umieść rozpoznawacz .mlmodel i opcjonalne lm6B.bin w katalogu `models/` obok `app/`. Zweryfikuj je skryptem `scripts/verify_models.py`. Modele pobierz z zatwierdzonego repozytorium HF; katalogu models nie zapisuj do repozytorium kodu. BLLA do segmentacji pochodzi z instalacji Kraken 7.0.2 (`kraken/blla.mlmodel`); nie jest nowym modelem Rej. Nie pobieramy modeli automatycznie przy starcie.

## KenLM jest opcjonalny

RAW i segmentacja nie wymagają KenLM. Do Diariusz LM potrzebne jest wiązanie z `MAX_ORDER>=6`. W pierwotnym środowisku używano lokalnego Windows builda KenLM 0.2.0 z MAX_ORDER=6. Numer wersji nie dowodzi zgodności binarnej. Nie dołączamy gotowych DLL/PYD ani środowiska właściciela.

Upstream https://github.com/kpu/kenlm dokumentuje budowę modułu Python i zmienną MAX_ORDER. Dla przygotowanego środowiska kompilacji można zacząć od `$env:MAX_ORDER='6'` i `python -m pip install kenlm==0.2.0`, lecz nie jest to przetestowany instalator Windows tego wydania. Do czasu potwierdzenia builda używaj RAW. Nie włączaj WSL, Dockera ani płatnego serwera jako części tej instalacji domyślnie.

## Start

```powershell
python scripts/verify_models.py --directory models
python app/serwer_gui.py
```

Otwórz ręcznie http://127.0.0.1:5057 . Opcja `--open-browser` otwiera przeglądarkę na wyraźne życzenie. Inny katalog modeli ustaw przez `REJ_MODEL_DIR`, inny port przez `REJ_PORT`. Port publikacyjnej kopii jest inny od działającej instalacji właściciela. Domyślne urządzenie to CPU; jeden proces geometrii i dwa wątki sieci. Pamięć sprawdzana jest przed segmentacją (rezerwa co najmniej 3,5 GiB plus budżet procesu geometrii); nie jest to gwarancja maksymalnego zużycia.

Przycisk lokalnego GPU jest opcjonalny. Do segmentacji wymaga wskazania przez REJ_GPU_LOCK istniejącej blokady uzgodnionej z innymi procesami użytkownika. To mechanizm współpracy, a nie automatyczne wykrywanie wszystkich treningów. Domyślnie nie używaj GPU przy aktywnym treningu. Nie jest to konfiguracja GPU Spaces ani płatnego hostingu.

Wybierz folder kopii skanów przeznaczonych do pracy. Aplikacja zapisuje obok skanów `.txt`, `__ocr.json`, `_podglad_segmentacji/`, `_historia_ocr/`, poprawki oraz raporty HTML. Plik tekstowy i bieżący raport mogą zostać zastąpione przy kolejnym odczycie; historia wariantów zachowuje wcześniejsze wyniki. Logi i rejestr raportów powstają w app/. Nie obejmuje ich publikacja źródeł.

Segmentacja wymaga ręcznej kontroli: kolejność kolumn i pominięte marginalia mogą wpływać na wynik bardziej niż sam dekoder. Dla OCR pojedynczego gotowego wiersza użyj `--no-segmentation` w ocr_batch.py. Tego przełącznika nie używaj na pełnej stronie.

## Pipeline bez interfejsu

Plik images.tsv zawiera w każdej linii pełną ścieżkę obrazu, tabulator i obrót 0/90/180/270. Z katalogu repozytorium:

```powershell
python app/segment_preview.py --images images.tsv --preview-dir preview --device cpu --layout auto --cpu-workers 1
python app/ocr_batch.py --model models/MikolajRej-KRA-K11-E26-step345005.mlmodel --images images.tsv --preview-dir preview --device cpu --layout auto
python app/report_gen.py --folder SCANY --out SCANY/_RAPORT_OCR.html --model "Rej E26 RAW"
```

Po przygotowaniu KenLM dodaj do drugiego polecenia `--lm models/lm6B.bin --lm-name Diariusz --alpha 0.5 --beta 1 --beam 64`. Zachowaj oryginalny skan, geometrię i RAW. Cache obejmuje tożsamość obrazu, obrót i wersję segmentacji. Raporty lokalne mogą zawierać ścieżki i historię dokumentów; do publicznej prezentacji użyj przygotowanych examples/ oraz docs/showcase/.

## Sprawdzenie kopii publikacyjnej

Przeprowadzono kontrolę składni, metadanych modelu i lekkie testy serwera/konfiguracji oraz kolejności czytania. Nie uruchamiano tu frameworka, sieci segmentacji ani OCR. Nie wykonano od początku instalacji i przetwarzania pełnej strony. Nie należy utożsamiać testu interfejsu z potwierdzeniem działania całego nowego środowiska. Pierwotny eksport miał wcześniej zapisany test CPU dwóch znanych wierszy.


Pliki do pobrania: [MikołajRej na Hugging Face](https://huggingface.co/lukaszrzepinski/MikolajRej/tree/main). Kod pełnej aplikacji: [repozytorium GitHub](https://github.com/lukaszrzepinski-gmail/mikolaj-rej-ocr).
