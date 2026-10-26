# Wyniki i granice pomiaru

| Domena | Wiersze | RAW | KorBa (porównanie) | Diariusz LM |
|---|---:|---:|---:|---:|
| Listy CDIAL | 37 | 8.922% | 8.383% | 4.611% |
| Diariusz | 24 | 3.067% | 3.395% | 1.314% |
| Psałterz | 17 | 7.872% | 10.787% | 8.163% |
| Rozmyślanie | 24 | 11.285% | 17.167% | 10.324% |
| Ortyle | 8 | 4.789% | 8.451% | 4.789% |


To **RAW110 pseudo DEV**: 110 znanych wierszy z odziedziczonymi etykietami pseudo/silver. Używano go do wyboru epoki. Nie jest niezależnym testem ani zbiorem human gold. Nie potwierdzono braku wcześniejszej ekspozycji modeli przodków ani korpusów LM.

| Miara | RAW E26 | E26 + Diariusz LM |
|---|---:|---:|
| Macro CER, równa waga 5 domen | 7,186787% | 5,840251% |
| Micro CER | 315/4114 = 7,656782% | 220/4114 = 5,347594% |
| Wiersze identyczne z pseudo referencją | 22/110 | 38/110 |
| Błędy cyfr / cyfr referencyjnych | 4/9 | 0/9 |
| D17, NFC CER, 17 znanych stron | 1742/17503 = 9,952580% | 1528/17503 = 8,729932% |

Macro jest średnią ilorazów błędów/znaków w pięciu domenach. Wynik 1,314% dla Diariusza dotyczy **24 wierszy i 913 znaków**, a nie całych 17 stron. D17 zachowuje wszystkie 495 pól segmentacji; referencję przygotował Claude i obejrzał właściciel, bez udokumentowanej niezależnej korekty znak po znaku. Marginalia i dopiski nie są w niej kompletne. Nie łączyć tych pomiarów w jeden benchmark.

Dziewięć cyfr i trzy sekwencje to zbyt mało, by wnioskować o skuteczności odczytu dat. W RAW110 nie ma oznaczonych wystąpień nazw własnych, więc nie podajemy wyniku ich ochrony. Poprawa CER z LM nie jest dowodem poprawności nazw, liczb lub wierności dyplomatycznej. Na Psałterzu Diariusz LM pogorszył wynik 7,872% → 8,163%.

LM oceniono na tych samych forwardach CTC: α=0,5, β=1, beam=64, cutoff=0,001, temperatura=1. Wynik systemu z LM jest odrębny od jakości samych wag. KorBa jest wyłącznie kolumną porównawczą; nie jest dołączonym artefaktem.

K11 zakończył się naturalnie na E31/global389675. E26/global345005 pozostaje wybraną wersją według tego pseudo DEV. Późniejsze próby Kraśnik/HANA są osobnymi eksperymentami i nie stanowią tej publikacji. Namespace/nazwisko w podziale nie dowodzi niezależności pisarzy ani ksiąg.

Cel CER ≤4% dla Diariusza i <8% dla rzeczywiście nieznanych źródeł, z ochroną nazw i cyfr, **nie został potwierdzony**.

W tym przygotowaniu publikacji nie uruchamiano OCR, treningu ani ciężkiej oceny. Wartości przepisano z zachowanych wyników, a agregaty sprawdzono. Nie publikujemy referencji DEV/TEST ani oryginalnego raportu z osadzonymi referencjami.
