# Nomenclature du prototype (BOM) — design Phase 6

> **Total ≈ 1 445 MAD**, dont **592,90 MAD vérifiés (41 %)** et **≈ 852 MAD estimés (59 %)**.
> Un prix est **[VÉRIFIÉ]** uniquement si la fiche produit réelle a été ouverte et le prix lu le 2026-10-21 (vendeur + URL au dossier Phase 6). Tout autre prix est **[ESTIMATION]** — figure de planification, jamais un prix constaté. Conversion déclarée : 1 USD = 10 MAD. Livraison vers le Maroc non comptée (non affichée sur les pages ouvertes).
> Le plafond initial de 700 MAD n'est **pas tenu** (×2,06) : les deux postes dominants (transmetteurs ; manifold d'égalisation) portent des fonctions obligatoires de la spécification. Aucune réduction conforme à la spécification n'a été trouvée. Le dossier de concours énonce le coût réel.

## Postes principaux

| # | Article (spécification du design) | Qté | Prix unit. (MAD) | Total (MAD) | Provenance |
|---|---|---|---|---|---|
| 1 | Transmetteur HTsensor BP155/BP15X — à commander : 0–600 kPa, sortie 0,5–4,5 V @ 5 VDC, filetage G1/4 (code J3), membrane 316L | 2 | 150,00 | **300,00** | [VÉRIFIÉ] 15,00 USD, Made-in-China (Hengtong) |
| 2 | Manifold d'égalisation laiton complet (tubes montants, tés, pointeaux, vanne boisseau, purges, adaptateurs, plaque) | 1 | ≈ 321 | **≈ 321** | [ESTIMATION] — détail au dossier Phase 6 §1 |
| 3 | Chaîne d'acquisition (ADS1115 + translateur de niveau + connectique) | 1 | 109,90 | **109,90** | [VÉRIFIÉ] (détail au dossier) |
| 4 | Affichage + capteurs annexes (LCD 1602, DS18B20 étanche, voyant, buzzer) | 1 | 129 | **129** | [VÉRIFIÉ] (détail au dossier) |
| 5 | ESP32-WROOM-32 module nu | 1 | ≈ 90 | **≈ 90** | [ESTIMATION] — DevKit 139 MAD [VÉRIFIÉ, rupture de stock] réservée au banc |
| 6 | DS3231 (module ZS-042 à modifier) | 1 | 40 | **40** | [VÉRIFIÉ] moussasoft.com |
| 7 | microSD + support | 1 | ≈ 60 | **≈ 60** | [ESTIMATION] |
| 8 | Énergie : 3×18650 génériques + support 3P + protection 1S + MCP1700 + MT3608 discret | 1 | ≈ 145 | **≈ 145** | mixte — cellules 18 MAD [VÉRIFIÉ, **capacité non annoncée**] ; reste [ESTIMATION] |
| 9 | Boîtier (objectif IP65 par construction) + presse-étoupes + câblage | 1 | ≈ 250 | **≈ 250** | [ESTIMATION] |
| | **TOTAL BOM PROTOTYPE** | | | **≈ 1 445 MAD** | 592,90 vérifiés / ≈ 852 estimés |

## Alternatives documentées

- **Transmetteur :** Wotian PCM303D « 600K » — 160 MAD conv. [VÉRIFIÉ : 0–600 kPa exact, 0,5–4,5 V @ 5 VDC, 0,5 %FS ; filetage à confirmer]. Le différentiel eau/eau bas coût n'a **pas été trouvé** dans la recherche du dossier (seule fiche différentielle ouverte : gaz uniquement, écartée) → l'architecture à deux jauges est la seule voie sourcée.
- **Cellules :** si le test de capacité échoue, cellules de marque ≈ 75 MAD/pièce [ESTIMATION] → total ≈ 1 616 MAD. La décision se prend sur la mesure, pas avant.
- **Boost :** module MT3608 9,50 MAD conv. [VÉRIFIÉ] en repli du discret.

## Outillage de banc (hors BOM produit)

Multimètre DT-9205 Plus 109 MAD [VÉRIFIÉ] · manomètre de référence glycérine 0–10 bar ≈ 180 MAD [ESTIMATION — achat local à relever] · pied à coulisse + peignes à filetage ≈ 150 MAD [ESTIMATION] · kit fer à souder ≈ 120 MAD [ESTIMATION] · petit outillage ≈ 80 MAD [ESTIMATION]. Coût total vers prototype validé estimé au dossier : ≈ 2 925–4 045 MAD (appareil + banc) — **estimation de planification**.
