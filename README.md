# Knjižnica

Majhna knjižnica: administrator upravlja knjige, študenti jih rezervirajo.
Flask + SQLite, brez dodatnih odvisnosti.

## Zagon

```bash
pip install -r requirements.txt   # samo Flask
python3 app.py                    # http://localhost:5000
```

Baza `knjiznica.db` se ustvari ob prvem zagonu in napolni s 16 knjigami.

## Demo računi

| Vloga   | E-pošta              | Geslo        |
|---------|----------------------|--------------|
| Študent | ana@student.si       | student123   |
| Admin   | admin@knjiznica.si   | admin123     |

Registracija administratorja zahteva kodo `KNJIZNICA-ADMIN`
(spremeni z okoljsko spremenljivko `KNJIZNICA_ADMIN_CODE`).

## Funkcionalnosti

- Registracija / prijava (študent, administrator), gesla so zgoščena
- Katalog z naslovnico, naslovom, avtorjem in razpoložljivostjo
- Iskanje po naslovu, avtorju ali kategoriji + filter kategorij, »samo razpoložljive«, razvrščanje
- Podrobnosti knjige z opisom in številom preostalih izvodov
- Rezervacija / preklic (atomarno zmanjša / povrne število izvodov)
- »Moje rezervacije« z aktivnimi in zgodovino
- Nadzorna plošča: dodajanje, urejanje, brisanje knjig, pregled in zaključevanje vseh rezervacij

Naslovnice se generirajo samodejno; administrator lahko vnese tudi URL slike.
