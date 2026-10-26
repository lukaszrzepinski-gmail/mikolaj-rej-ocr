# Lokalny odczyt obrazu z gotową segmentacją PAGE

Model jest rozpoznawaczem tekstu w wierszach. Potrzebuje obrazu oraz odpowiadającego mu PAGE XML z liniami bazowymi (`Baseline`) i obrysami wierszy (`Coords`). Sam plik modelu nie wykrywa układu strony ani kolumn. Segmentację przygotuj osobno i sprawdź jej kolejność odczytu.

Skrypt `scripts/recognize_page.py` wykonuje odczyt na CPU, domyślnie z dwoma wątkami. Korzysta z domyślnego dekodera greedy CTC Krakena. Nie dodaje modelu językowego, słownika, normalizacji Unicode ani korekty nazw i cyfr. Kraken nadal stosuje swój standardowy preprocessing i porządkowanie Unicode BiDi. Plik wynikowy zawiera identyfikatory wierszy i surowe predykcje, bez przepisywania referencji z XML.

## Środowisko

Oryginalny eksport i dwuwierszowy test obrazu wykonano w Pythonie 3.12.13, Krakenie 7.0.2, PyTorch 2.10.0+cu128, torchvision 0.25.0+cu128, coremltools 9.0 i Pillow 12.3.0. Test działał na CPU pomimo obecności bibliotek CUDA. Instalacja poniżej wybiera koła CPU; jej zgodności nie potwierdzono wykonaniem modelu w tym pakiecie.

Preferowany punkt startowy to osobne środowisko Python 3.12 na Linuxie z kołami CPU. Utwórz je poleceniem `python3.12 -m venv .venv` i aktywuj przez `source .venv/bin/activate`, następnie wykonaj dwa polecenia `pip` poniżej. Na Windows odpowiednikiem jest:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install torch==2.10.0 torchvision==0.25.0 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
```

Koła z indeksem CPU powyżej dotyczą platform obsługiwanych przez ten indeks; na macOS użyj oficjalnej instalacji CPU PyTorch dla swojej platformy. Nie instaluj tych zależności do środowiska działającego treningu. Lista przypina bezpośrednie zależności, ale nie jest pełnym lockfile wszystkich bibliotek. Różnice platform i wariantów CPU/CUDA nie zostały tutaj zweryfikowane eksperymentalnie.

## Wejście

Pobierz opublikowany plik `.mlmodel` i jego manifest z zatwierdzonego repozytorium modelu. Wartość `--model-sha256` musi pochodzić z tego manifestu i dotyczyć dokładnie pobranej wersji pliku. Kopia z oczyszczonymi metadanymi ma inny skrót niż pierwotny eksport GUI, choć wagi są zachowane. Skrypt nie pobiera modelu ani plików automatycznie.

Zapisz własny obraz np. `page.png` i jego segmentację `page.xml` w jednym katalogu. Pole `Page imageFilename` w XML musi wskazywać ten obraz, a `imageWidth` i `imageHeight` muszą odpowiadać jego wymiarom. Współrzędne muszą odnosić się do podanego obrazu; po skalowaniu, obrocie lub przycięciu trzeba dostosować XML. Skrypt odrzuca brakujące linie bazowe/obrysy, zduplikowane identyfikatory wierszy i XML z deklaracją DTD/encji. Nie wymaga tekstów referencyjnych `TextEquiv`.

## Uruchomienie

Z katalogu repozytorium, po podstawieniu rzeczywistego SHA256 z manifestu:

```powershell
python scripts/recognize_page.py --model model.mlmodel --model-sha256 SHA256_Z_MANIFESTU --image page.png --page-xml page.xml --output raw-predictions.json --threads 2
```

`SHA256_Z_MANIFESTU` jest oznaczeniem miejsca do podstawienia 64 znaków szesnastkowych, a nie poprawnym argumentem. Katalog wyniku musi istnieć, a plik wynikowy musi być nowy. Skrypt nie nadpisuje plików. Wymagania pamięci zależą od rozdzielczości strony i długości wierszy; dla tej wersji nie zmierzono granicznej ilości RAM ani czasu odczytu.

## Zakres sprawdzenia

Nowy wrapper sprawdzono składniowo i przez przegląd zgodności z lokalnie zainstalowanym API Kraken 7.0.2. Nie importowano ani nie uruchamiano frameworka w trakcie przygotowania publikacji. Nie wykonano tym wrapperem ponownego OCR ani pełnej ewaluacji. Wcześniejszy, zapisany test dwóch znanych wierszy dotyczy pierwotnego eksportu GUI, nie nowej instalacji CPU i nie niezależnych danych testowych.

Kod zachowuje starszy interfejs `load_any` / `XMLPage.to_container` / `rpred` użyty w tamtym teście. Kraken 7.0.2 oznacza `rpred` jako przestarzały, dlatego skrypt wymaga tej wersji. Nie należy zakładać zgodności z Krakenem 8.

## Źródła techniczne

- [Oficjalne zależności Kraken 7.0.2](https://github.com/mittagessen/kraken/blob/7.0.2/pyproject.toml).
- [Oficjalny interfejs rozpoznawania Kraken 7.0.2](https://github.com/mittagessen/kraken/blob/7.0.2/kraken/rpred.py).
- [Oficjalny loader modelu Kraken 7.0.2](https://github.com/mittagessen/kraken/blob/7.0.2/kraken/lib/models.py).
- [Oficjalny parser PAGE XML Kraken 7.0.2](https://github.com/mittagessen/kraken/blob/7.0.2/kraken/lib/xml/__init__.py).

Dokumentację zależności sprawdzono w oficjalnym źródle; sygnatury API dodatkowo odczytano z zainstalowanego Krakena 7.0.2 bez importowania bibliotek.


Pliki do pobrania: [MikołajRej na Hugging Face](https://huggingface.co/lukaszrzepinski/MikolajRej/tree/main). Kod pełnej aplikacji: [repozytorium GitHub](https://github.com/lukaszrzepinski-gmail/mikolaj-rej-ocr).
