# Architecture du prototype (design — Phase 6 du dossier)

> État : **conçu, non construit.** La porte **G0** — confirmation écrite du fournisseur sur la tenue en surpression des transmetteurs et la tolérance d'alimentation — précède tout achat.

## 1. Hydraulique

- Deux prises de pression (amont/aval du filtre) montent chacune par un **tube montant** (250–400 mm) jusqu'à son transmetteur ; les deux transmetteurs sont fixés sur une **plaque commune horizontale, faces sensibles à la même cote à ±5 cm près** (≈ 0,49 kPa) — condition de vérité du contrôle de zéro.
- Entre les tubes : **ligne transversale d'égalisation** horizontale à **vanne à boisseau sphérique unique** (organe du contrôle de zéro).
- Par côté : adaptateur de piquage → tube montant → té de dérivation → **vanne pointeau** (isolement + amortisseur réglable contre les coups de bélier) → té de sommet (purge d'air + transmetteur).
- Tout laiton fileté, étanchéité PTFE, **zéro soudure**. Boîtier : objectif IP65 par construction + test d'aspersion au banc, **non certifié**.
- Entrées de câbles par presse-étoupes PG7 en partie basse, boucles d'égouttement, étiquettes AMONT/AVAL aux deux extrémités.

## 2. Électronique

| Bloc | Choix de design | Raison |
|---|---|---|
| MCU | **ESP32-WROOM-32, module nu** | Une DevKit non modifiée consomme 5–10 mA en deep-sleep (régulateur, pont USB, LED) → ≈ 29 jours : échec de la cible d'autonomie. Module nu obligatoire ; DevKit réservée au développement banc. |
| CAN | **ADS1115, alimenté en 5 V commuté**, PGA ±6,144 V, translateur I2C BSS138 | Le CAN interne ESP32 est exclu (≈ ±4,5 kPa équivalents d'erreur). La gamme ±4,096 V saturerait (sortie transmetteur 4,5 V ; rail 5 V sur AIN3). LSB résultant 0,028 kPa ≈ 100× plus fin que U(E). |
| Voies ADS1115 | AIN0 = P_amont · AIN1 = P_aval · AIN3 = rail 5 V d'excitation | L'ADS1115 a une référence interne : la mesure n'est ratiométrique que si l'on **mesure le rail d'excitation** et que l'on divise — c'est le rôle d'AIN3. |
| Transmetteurs | 0,5–4,5 V @ 5 VDC, alimentés par le boost commuté | Excitation coupée entre rafales (consommation) ; temps de chauffe respecté avant conversion. |
| RTC | **DS3231** (module ZS-042 modifié), VCC commutée, tenue d'heure sur CR2032 | Horodatages monotones ; journal en UTC ; compteur de démarrages + détection de saut d'heure. |
| T_eau | DS18B20 étanche, té sur conduite amont | 1 conversion par agrégat de 5 min (conversion lancée à la rafale précédente). |
| Stockage | microSD native 3,3 V, alimentation commutée | Écriture ouvrir/ajouter/flush/fermer par enregistrement (voir format de données). |
| Affichage | LCD 1602 + voyant tricolore + buzzer | ΔP courante, E courant, état, date du dernier contrôle de zéro. Alimentés seulement en session éveillée / alarme. |
| Énergie | Pack **1S 3×18650** + carte de protection 1S, LDO **MCP1700-3302E**, boost **MT3608** discret commuté (5 V) | Voir budget §3. |

## 3. Budget d'énergie (calcul — non mesuré)

- Réveil en **rafale ≤ 2,5 s** par minute (mesures), deep-sleep entre rafales, rails capteurs/affichage/SD commutés.
- Consommation calculée ≈ **47,3 mAh/jour** → **≈ 130 jours** sur capacité utile de planification 6 160 mAh, soit +45 % sur la cible ≥ 3 mois — **sous conditions** : module nu, rafale tenue, et capacité réelle des cellules ≈ 2 600 mAh.
- ⚠ Les cellules bon marché vérifiées **n'annoncent aucune capacité** : le pack assemblé passera un **test de capacité au banc** avant toute revendication d'autonomie ; variante cellules de marque en repli (+171 MAD estimés).
- Seuils firmware : alerte batterie **3,45 V**, arrêt propre **3,35 V**, brown-out ESP32 actif. La coupure de la carte de protection (~2,4–2,5 V) est un dernier filet, jamais atteint en service normal.

## 4. Modes du firmware

`COMMISSION` (étalonnage volumétrique, capture B_0) · `RUN` (surveillance + alarme) · `ZERO_CHECK` (égalisation guidée) · `FAULT` (SD absente, capteur hors plage, batterie critique). Détail : [06-method.md](06-method.md) et `firmware/`.
