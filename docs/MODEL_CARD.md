# MikołajRej — E26 i Diariusz LM

Autor nowego wkładu: **Łukasz Rzepiński**. Eksperymentalny rozpoznawacz historycznych rękopisów polskich i łacińskich w formacie Kraken .mlmodel, z opcjonalnym znakowym Diariusz LM. Obsługuje rozpoznawanie wierszy; pełna aplikacja dodaje segmentację, kolumny, kolejność czytania, galerię i raporty. Nie ma tu działającego płatnego endpointu ani publicznego serwera OCR.

## Artefakty

| Plik | Bajty | SHA256 |
|---|---:|---|
| MikolajRej-KRA-K11-E26-step345005.mlmodel | 16 437 242 | `871092c802375e0100c1b2efefb2dcf687b87022f2305723dfffb9aeef5e243d` |
| lm6B.bin | 61 757 330 | `7545861f8b82a5b4d8ecce74e057c720fadc7683c7aa2302bc63fd500b666bff` |

Wybrano E26/global345005 po naturalnym zakończeniu K11 na E31. W kopii publikacyjnej usunięto lokalne ścieżki z metadanych; cały zapis sieci, alfabet i ustawienia przetwarzania pozostają identyczne z wcześniej sprawdzonym eksportem GUI. Oryginalny eksport SHA256 zaczyna się od `195ea0b2`; nowa kopia ma inny hash. Pełny checkpoint treningowy (w tym stan optymalizatora) nie jest artefaktem dystrybucyjnym. Szczegóły: provenance.json.

## Wyniki

**RAW110 jest pseudo DEV używanym do selekcji epoki, nie niezależnym testem.** RAW: macro CER 7,186787%, micro 315/4114 = 7,656782%. Z Diariusz LM: macro 5,840251%, micro 220/4114 = 5,347594%. Wyniku LM nie przypisujemy samym wagom.

| Domena | Wiersze | RAW | KorBa (porównanie) | Diariusz LM |
|---|---:|---:|---:|---:|
| Listy CDIAL | 37 | 8.922% | 8.383% | 4.611% |
| Diariusz | 24 | 3.067% | 3.395% | 1.314% |
| Psałterz | 17 | 7.872% | 10.787% | 8.163% |
| Rozmyślanie | 24 | 11.285% | 17.167% | 10.324% |
| Ortyle | 8 | 4.789% | 8.451% | 4.789% |


1,314% dla Diariusza obejmuje 24 wiersze i 913 znaków. Na znanym D17 (17 stron, 17 503 znaki NFC) RAW wynosi 9,952580%, z LM 8,729932%; referencja ma opisane ograniczenia. Dziewięć cyfr w RAW110 nie wystarcza do oceny dat, a nazw własnych nie oznaczono. Cel misji nie jest potwierdzony. Pełny opis i agregaty: [EVALUATION.md](EVALUATION.md), metrics.json.

## Pochodzenie i trening

Nazwana baza: McCATMuS_nfd_nofix_V1, autorzy i licencja w NOTICE.md. Następnie Argon/Rej, bulk i kontynuacja K11 na 71 470 wewnętrznie dopuszczonych wierszach, głównie pseudoetykietach. Nie odzyskano pełnego historycznego łańcucha pierwszego wejścia i membership. Model tej publikacji nie jest późniejszym eksperymentem Kraśnik/HANA. [DATA_PROVENANCE.md](DATA_PROVENANCE.md) opisuje pochodzenie i braki dokumentacji praw; nie deklarujemy niezależności wszystkich źródeł.

## Użycie lokalne

Kraken **7.0.2**, Python **3.12**, PyTorch **2.10.0**. Wejście rozpoznawacza: skala szarości L, baseline segmentation, wysokość sieci 120, legacy polygons false, 293 symbole codec + blank CTC. Format .mlmodel jest ładowany przez Kraken; nie jest modelem Transformers. Przykłady zawierają obraz, PAGE XML z geometrią bez TextEquiv i wcześniej zapisany RAW.

Instrukcja wrappera: [LOCAL_INFERENCE.md](LOCAL_INFERENCE.md). Pipeline i aplikacja: [WEB_APP.md](WEB_APP.md). Diariusz LM i KenLM: [DIARIUSZ_LM.md](DIARIUSZ_LM.md). Przykłady: [examples/README.md](../examples/README.md).

Nowy wrapper i instalacja nie zostały uruchomione z frameworkiem w tym przygotowaniu. Wcześniejszy smoke oryginalnego eksportu obejmował dwa znane wiersze. Sanitizację sprawdzono przez identyczność bajtów poza opisanym fragmentem metadanych; nie wykonano ponownego OCR oczyszczonej kopii.

## Ograniczenia i przeznaczenie

Pomoc w badaniach, transkrypcji i przeglądzie archiwaliów z ręczną kontrolą. Segmentacja, obrót, kolumny i pominięte dopiski mogą zmienić wynik. LM może zastąpić poprawny rzadki wyraz częstszym, zmienić nazwisko lub cyfrę. Zachowuj skan i RAW. Model nie zastępuje edycji krytycznej, dowodu genealogicznego ani weryfikacji treści dokumentu. Jakość na rzeczywiście nieznanych księgach/pisarzach nie została tu niezależnie ustalona.

## Licencja i autorstwo

Własny chroniony wkład Łukasza Rzepińskiego: użycie niekomercyjne z atrybucją; komercyjne za odrębną pisemną zgodą. To **nie MIT**. Zakres i wyłączenia określają LICENSE i NOTICE.md. Oryginalny McCATMuS pozostaje CC BY 4.0; te warunki nie odbierają praw upstream ani nie ograniczają domeny publicznej. Pełny rejestr praw do dodatkowych danych oraz dokładny korpus Diariusz LM nie zostały odtworzone. Publikacja zachowuje jawny opis tych braków; nie stanowi deklaracji pełnego odtworzenia historii danych.

## Projekt zrodlacyfrowe.pl

[zrodlacyfrowe.pl](https://zrodlacyfrowe.pl/) to projekt przetwarzania zasobów archiwalnych przy użyciu sztucznej inteligencji. MikołajRej OCR jest narzędziem wspierającym rozpoznawanie i opracowanie tekstu historycznych dokumentów.


## Kod i aplikacja

[Kod aplikacji webowej, segmentacja i pipeline](https://github.com/lukaszrzepinski-gmail/mikolaj-rej-ocr). [Pliki modelu i Diariusz LM](https://huggingface.co/lukaszrzepinski/MikolajRej/tree/main).
