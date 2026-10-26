# MikołajRej OCR

Lokalna aplikacja webowa do historycznych rękopisów: galeria skanów → segmentacja → kolumny i kolejność czytania → Kraken E26 → opcjonalny Diariusz LM → raport skan ↔ tekst, historia wariantów i poprawki.

Autor nowego wkładu: **Łukasz Rzepiński**. Komercyjne wykorzystanie jego praw wymaga odrębnej pisemnej zgody; zachowaj atrybucję i warunki LICENSE. McCATMuS, Kraken, KenLM oraz domena publiczna mają odrębne zakresy praw w NOTICE.md.

- [Instalacja aplikacji, pipeline i segmentacji](docs/WEB_APP.md)
- [Wrapper OCR z gotowym PAGE XML](docs/LOCAL_INFERENCE.md)
- [Model card](docs/MODEL_CARD.md), [wyniki i ograniczenia](docs/EVALUATION.md)
- [Diariusz LM](docs/DIARIUSZ_LM.md), [pochodzenie danych](docs/DATA_PROVENANCE.md)
- [Przykłady skan → RAW](examples/README.md), [statyczna prezentacja](docs/showcase/index.html)

Model E26 ma macro CER 7,19% na **RAW110 pseudo DEV używanym do wyboru epoki**. To nie niezależny benchmark human gold. Z Diariusz LM wynik całego systemu wynosi 5,84% macro na tym samym zbiorze. Nie potwierdzono celu jakości na rzeczywiście nieznanych źródłach.

[Wagi MikołajRej i Diariusz LM](https://huggingface.co/lukaszrzepinski/MikolajRej/tree/main) są udostępnione w osobnym repozytorium modelu HF; nie dodawaj ich do repozytorium kodu. Umieść pobrane artefakty w models/ i uruchom `python scripts/verify_models.py --directory models`. Następnie w przygotowanym środowisku Python 3.12: `python app/serwer_gui.py` i http://127.0.0.1:5057 . Pełna aplikacja ma kontrolę zasobów Windows i domyślnie używa CPU. Instalacja od zera i OCR w nowym środowisku nie zostały tu wykonane; szczegółowy zakres sprawdzenia jest w instrukcji.

Repozytorium udostępnia kod do lokalnego uruchomienia. Samo opublikowanie kodu nie uruchamia serwera, GPU Spaces, endpointu ani subskrypcji. Raporty i historia użytkownika powstają dopiero lokalnie i nie są przykładowymi danymi repozytorium.

## Projekt zrodlacyfrowe.pl

[zrodlacyfrowe.pl](https://zrodlacyfrowe.pl/) to projekt przetwarzania zasobów archiwalnych przy użyciu sztucznej inteligencji. MikołajRej OCR jest narzędziem wspierającym rozpoznawanie i opracowanie tekstu historycznych dokumentów.

