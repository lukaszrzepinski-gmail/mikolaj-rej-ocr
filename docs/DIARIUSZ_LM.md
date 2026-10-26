# Diariusz LM — znakowy KenLM 6-gram

Plik: `lm6B.bin`, 61 757 330 bajtów, SHA256 `7545861f8b82a5b4d8ecce74e057c720fadc7683c7aa2302bc63fd500b666bff`.

Jest osobnym statystycznym modelem językowym stosowanym po forwardzie CTC rozpoznawacza. Nie zawiera wag E26 i nie wykonuje segmentacji obrazu. Dekoder zamienia spację na token `▁` i przetwarza znaki w NFD. Zachowano dwa historyczne algorytmy `beam_lm` i `lm_krok`; AST w Pythonie 3.12: `2e5ff1322e353fd79dec7478b6c226090ed279775b2f995ce3d35d61f60c2dd3`.

Ustawienia raportowanego pomiaru: α=0,5, β=1, beam=64, cutoff=0,001, temperatura=1. LM jest opcjonalny. Aplikacja domyślnie startuje w RAW; wybór LM jest jawny. RAW pozostaje zapisany w wynikach także przy pracy z LM.

Użycie wymaga osobno zainstalowanego wiązania Python KenLM z `MAX_ORDER` co najmniej 6. Oryginalne środowisko miało KenLM 0.2.0, Python 3.12, lokalny build Windows z `MAX_ORDER=6`. Gotowego binarium rozszerzenia nie dołączamy. Nie wykonano tu ponownej instalacji ani próby załadowania LM w nowym środowisku. Samo `pip install kenlm` nie gwarantuje zgodnego builda na Windows. Szczegóły: [uruchomienie aplikacji](WEB_APP.md).

To historyczny LM o niekompletnym powiązaniu z korpusem budowy. Brak dokumentacji pozwalającej zapewnić czystość DEV/TEST i komplet praw do tekstów wejściowych opisuje [pochodzenie](DATA_PROVENANCE.md). Wyniki z LM mogą poprawiać średni CER, ale również zmieniać poprawne nazwy i cyfry. Zachowaj RAW, podgląd skanu i ręczną kontrolę.

Warunki własnego wkładu autora określa LICENSE, z zachowaniem cudzych praw i domeny publicznej.

## Wskazane źródło Diariusza

Właściciel projektu wskazuje jako źródło Diariusz Michała Kazimierza Radziwiłła „Rybeńki”, przechowywany w AGAD i należący do domeny publicznej. Identyfikacja rękopisu w lokalnej dokumentacji: Archiwum Radziwiłłów, dział VI, sygn. II-80a (uwierzytelniona kopia). [Archiwum Radziwiłłów — AGAD](https://agad.gov.pl/?page_id=866). Historyczny rękopis i ewentualne współczesne edycje lub transkrypcje to odrębne materiały. Ta deklaracja pochodzenia nie zastępuje brakującego rejestru dokładnych wejść użytych do budowy konkretnego lm6B.bin.

