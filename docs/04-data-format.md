# Format de données — journal CSV (schéma v1)

Le journal est un fichier texte **CSV** sur carte microSD, lisible sur un ordinateur ordinaire sans logiciel propriétaire. Un fichier par mois (`DF-AAAA-MM.csv`). Écriture par enregistrement : ouvrir → ajouter → vider (flush) → fermer (jamais de fichier gardé ouvert ; protection contre les coupures d'alimentation).

## En-tête

La première ligne du fichier est un commentaire de version :

```
# deltafiltre-log schema=1 fw=0.1.0 device=DF-001
```

suivi de la ligne d'en-tête des colonnes.

## Colonnes

| Colonne | Unité | Description |
|---|---|---|
| `seq` | — | Numéro de séquence monotone (détecte les pertes d'enregistrements) |
| `boot` | — | Compteur de démarrages |
| `ts_iso8601` | — | Horodatage RTC, UTC, format ISO 8601 |
| `p_up_kpa` | kPa | Médiane 5 min de la pression amont |
| `p_down_kpa` | kPa | Médiane 5 min de la pression aval |
| `dp_kpa` | kPa | Médiane 5 min des ΔP par échantillon |
| `t_water_c` | °C | Température d'eau (1 mesure par agrégat) |
| `dp_norm_kpa` | kPa | ΔP normalisée à Q_ref (vide si non applicable) |
| `excess_kpa` | kPa | E = ΔP_norm − B_n (vide si fenêtre invalide) |
| `baseline_kpa` | kPa | Base en vigueur B_n |
| `alarm_state` | — | `OK`, `PENDING1`, `PENDING2`, `ALARM` |
| `vbat_v` | V | Tension batterie |
| `flags` | — | Drapeaux qualité, séparés par `|` (voir ci-dessous) |

## Drapeaux qualité (`flags`)

| Drapeau | Signification |
|---|---|
| `ZERO_UNVERIFIED` | Aucun contrôle de zéro valide récent ; données à interpréter avec réserve |
| `SENSOR_DRIFT_WARN` | Dernier contrôle de zéro : \|ΔP_zéro\| > tolérance (2 kPa) |
| `TIME_JUMP` | Saut d'horloge RTC détecté (remise à l'heure, pile RTC…) |
| `SD_FAULT` | Écriture SD échouée pour cet agrégat (donnée conservée en tampon si possible) |
| `SENSOR_OOR` | Lecture hors plage plausible (4–96 % de l'étendue du transmetteur) — rupture de fil suspectée |
| `NO_FLOW` | Pompe arrêtée / pas d'écoulement : fenêtre invalide pour l'alarme |
| `TRANSIENT` | Transitoire hydraulique détecté (démarrage, manœuvre) : fenêtre invalide |
| `LOW_BATT` | Batterie sous le seuil d'alerte (3,45 V) |

## Événements

Les événements sont journalisés comme des lignes dont `alarm_state` vaut `EVENT` et dont le champ libre en fin de ligne (`event` — colonne supplémentaire admise sur ces lignes) précise : `BOOT`, `BASE_CAPTURED` (avec B_n et r_n), `CLEANING_CONFIRMED`, `ZERO_CHECK` (avec ΔP_zéro mesurée), `ALARM_ON`, `ALARM_ACK`, `ALARM_OFF`, `TIME_SET`, `SHUTDOWN_LOW_BATT`.

## Règles d'intégrité

- Horodatages monotones croissants dans le journal ; tout saut est marqué `TIME_JUMP`.
- Aucune donnée n'est jamais réécrite ou « corrigée » a posteriori dans le journal.
- Les fichiers de données expérimentales futures vivront dans `data/` du dépôt avec leur contexte de protocole ; à ce jour, **aucune donnée expérimentale n'existe** (voir `data/README.md`).
