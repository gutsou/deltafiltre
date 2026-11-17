# Protocole de validation E0–E7 (pré-enregistré — **aucune étape exécutée**)

> Ce protocole est fixé **avant** les mesures. Ses critères d'acceptation ne seront pas modifiés après coup pour accommoder des résultats. Tout écart sera documenté comme amendement daté.
> **Porte G0 (bloquante, avant tout achat) :** confirmation **écrite** du fournisseur des transmetteurs sur (a) la tenue en surpression, (b) la tolérance de la tension d'alimentation. Sans G0, aucun achat, aucun assemblage.

| Étape | Objet | Critère principal (résumé) |
|---|---|---|
| E0 | Vérification documentaire et réception des composants | Conformité des références reçues aux fiches (plage, sortie, filetage, membrane) |
| E1 | Étalonnage au banc contre manomètre de référence | Écarts zéro/pleine échelle journalisés par transmetteur ; budget d'incertitude confronté au calcul (±1,6 kPa sur E) |
| E2 | Contrôle de zéro par égalisation (banc hydraulique) | ΔP_zéro mesurée répétée ; validation de la tolérance de 2 kPa ou amendement motivé |
| E3 | Loi du filtre propre ΔP = k·Qⁿ | Ajustement sur points volumétriques ; résidus journalisés ; reproductibilité de B_0 |
| E4 | Encrassement contrôlé au banc | Courbes ΔP(temps) à encrassement imposé ; comportement de la règle d'alarme |
| E5 | **Comparaison des règles sur les mêmes séries** : relative à la base vs témoin « seuil fixe 0,5 bar » | Taux de fausses alarmes, délai de détection, événements manqués — calculés par les scripts d'`analysis/` sur les séries journalisées |
| E6 | Autonomie | Test de capacité du pack assemblé (décharge contrôlée) ; consommation moyenne mesurée vs budget calculé (47,3 mAh/jour) |
| E7 | Pilote terrain (1 saison, 2–3 exploitations) + preuve de demande | Fonctionnement en conditions réelles ; **et** intérêt documenté d'un porteur (technicien, coopérative, installateur) pour le positionnement « instrument de diagnostic partagé » — sans porteur, le positionnement commercial tombe |

## Métriques déclarées à l'avance

Incertitude ΔP réalisée · fausses alarmes / semaine · délai de détection · événements manqués · reproductibilité de la base · autonomie mesurée · dérive de base post-nettoyage (r_n) sur la saison.

## Intégrité

- Aucun résultat n'existe à ce jour ; ce document ne contient que le **plan**.
- Les scripts d'analyse ont été exercés uniquement sur des **données synthétiques étiquetées** (voir `analysis/`), ce qui démontre la logique de calcul — **pas** la performance de la méthode.
- Si E5 montre que la règle relative à la base ne fait pas mieux que le seuil fixe 0,5 bar sur les mêmes séries, la différenciation de méthode tombe et le dossier devra le dire.
