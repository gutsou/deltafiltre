# analysis/ — scripts d'analyse hors ligne

Scripts Python (bibliothèque standard) issus de la Phase 8 du dossier : la boucle de validation logicielle du projet. Ils ont été exercés **uniquement sur des fixtures synthétiques étiquetées** — ils démontrent la logique de calcul, pas la performance de la méthode.

| Script | Rôle |
|---|---|
| `gen_fixtures.py` | Générateur déterministe des fixtures **SYNTHÉTIQUES** de test logiciel |
| `replay_ac04.py` | Rejeu hors ligne des séries : rejoue la règle d'alarme relative à la base sur un journal et la compare au témoin « seuil fixe 0,5 bar » sur les mêmes données (critère AC-04 / protocole E5) |
| `fit_kn.py` | Ajustement hors ligne (k, n) de la loi ΔP = k·Qⁿ à partir de points volumétriques (E1/E3) |
| `drift_e4.py` | Analyse de la dérive post-nettoyage B_n / r_n (E4 / AC-08) |

Quand les données réelles du protocole E0–E7 existeront, ces mêmes scripts les traiteront sans modification de la logique testée.
