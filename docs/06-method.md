# Méthode — alarme relative à la base propre

## 1. Grandeurs mesurées

- `P_amont`, `P_aval` : pressions relatives amont/aval du filtre (kPa), deux transmetteurs 0–600 kPa.
- `ΔP = P_amont − P_aval` : perte de charge du filtre.
- `T_eau` : température de l'eau (contexte ; variable lente).
- État pompe (marche/arrêt) : contexte de validité des fenêtres.

## 2. Loi du filtre propre et étalonnage de mise en service

Pour un filtre propre, la perte de charge suit une loi puissance du débit :

```
ΔP = k · Q^n        (Éq. 2 du dossier, Phase 4)
```

À la mise en service (filtre propre), l'utilisateur mesure le débit par **récipient gradué et chronomètre** en 2 points de régime au minimum (3 recommandés). Le produit ajuste (k, n) par régression log-log, fixe le débit de référence **Q_ref** et la fenêtre de régime de référence.

Normalisation, quand un débit estimé est disponible :

```
ΔP_norm = ΔP_mes · (Q_ref / Q_mes)^n
```

À défaut de débit estimé, seules les fenêtres conformes au régime de référence sont comparées à la base (drapeau de validité).

⚠ **Point faible assumé (à documenter devant tout jury) :** il n'y a **pas de capteur de débit**. Q est estimé, pas mesuré. Une erreur volumétrique de 5 % avec n ≈ 1,8–2 produit ≈ 10 % d'erreur sur ΔP (≈ 6 kPa à 60 kPa). C'est une limite de la méthode v1, déclarée — pas un détail caché.

## 3. Base propre

- **B_0** : ΔP du filtre propre à Q_ref, capturée à la mise en service, avec T_eau associée. Jamais une valeur d'usine.
- **B_n** : base re-capturée après chaque nettoyage confirmé par l'utilisateur.
- **r_n = B_n / B_0** : rapport de récupération, journalisé en continu comme **indicateur en cours de validation scientifique**. Aucune loi quantitative de dérive n'existe dans la littérature ouverte consultée ; l'indicateur n'est **jamais** présenté comme un diagnostic. En v1, son seuil d'affichage est désactivé par défaut.

## 4. Règle d'alarme (exclusivement relative)

```
E(t) = ΔP_norm(t) − B_n
Alarme :  E ≥ δ, persistant sur 3 fenêtres valides consécutives
Effacement : E < δ − h        avec h = 5 kPa (hystérésis)
δ : défaut 20 kPa, réglable 20–40 kPa
```

- Fourchette de δ fondée sur des critères documentés : AZUD (base + 0,2–0,3 bar) ; Hasani et al. (déclenchement à +40 kPa). La valeur par défaut et la persistance de 3 fenêtres sont des **choix** de conception, à régler sur les données du protocole E0–E7.
- Le produit n'embarque **aucun mode à seuil absolu fixe**. La règle « seuil fixe 0,5 bar » n'existe que comme **condition témoin d'analyse hors ligne**, évaluable a posteriori sur les mêmes séries journalisées.

## 5. Contrôle de zéro par égalisation

Configuration : pompe arrêtée, ligne immobile, vanne transversale d'égalisation ouverte, transmetteurs à même cote (±5 cm) reliés à un seul corps d'eau statique ⇒ la ΔP vraie aux capteurs est **0**. Tout ΔP mesuré est alors la somme des erreurs de zéro des deux transmetteurs.

- Si **|ΔP_zéro| > 2 kPa** (tolérance par défaut, cohérente avec U(E) ≈ ±1,6 kPa) : avertissement distinct **« dérive capteur suspectée »**, et les données depuis le dernier contrôle valide sont marquées **« zéro non vérifié »**.
- Sans contrôle de zéro valide, le suivi de dérive (§3) ne doit pas être présenté comme interprétable.
- Limite assumée : le contrôle ne détecte que l'erreur de **zéro**, pas la dérive de **sensibilité** (span).

## 6. Budget d'incertitude (calculs — Phase 4 du dossier)

| Grandeur | Incertitude élargie U (k = 2) | Origine |
|---|---|---|
| ΔP absolue (deux transmetteurs ±0,5–1 % PE 600 kPa) | ±5,9 à ±10,3 kPa | erreurs indépendantes des deux capteurs |
| Excès E = ΔP − B (même paire de capteurs) | **≈ ±1,6 kPa** | les erreurs constantes se compensent dans la différence |

C'est cette asymétrie qui rend la mesure possible à bas coût — à quatre conditions de validité : **mêmes capteurs, zéro contrôlé, températures d'époques voisines ou documentées, débit normalisé ou fenêtré**.

## 7. Agrégation et rejet des transitoires

- Échantillonnage ≥ 1 mesure/minute par voie (rafale de conversions à chaque réveil).
- Agrégat journalisé : **médiane sur 5 minutes** de P_amont, P_aval, ΔP et T_eau — la médiane rejette les transitoires hydrauliques (démarrage pompe, manœuvres de vannes, air).
- ΔP de fenêtre = médiane des différences par échantillon (et non différence des médianes).
- Les fenêtres hors régime (pompe arrêtée, transitoire) portent un drapeau d'invalidité et **n'alimentent jamais** le compteur de persistance de l'alarme.

## 8. Limites supplémentaires identifiées en revue externe (2026-11-17)

Revues croisées du design (Claude, Gemini — avis externes non vérifiés, confrontés au dossier) :

- **Dérive thermique non compensée en v1.** Les transmetteurs piézorésistifs ont des coefficients thermiques de zéro et de sensibilité non négligeables ; T_eau est journalisée comme **contexte** et la méthode exige des « températures d'époques voisines ou documentées » (§6), mais **aucune matrice de compensation (TC0/TCS) n'est appliquée** en v1. Question ouverte pour E1 : mesurer l'effet au banc avant de décider d'une compensation logicielle.
- **Risque d'erreur d'usage du contrôle de zéro.** Si la vanne d'égalisation reste ouverte après le contrôle, la ΔP d'irrigation est annulée et l'alarme devient aveugle. Atténuations de design : poignée de vanne visible au centre du manifold, procédure exigeant la pompe arrêtée, et le contrôle est un **mode explicite** du firmware — mais le risque d'oubli reste un risque d'usage déclaré, pas un risque éliminé.
- **Médiane de 5 valeurs par fenêtre** (1 mesure/minute, EF-04) : statistiquement mince. Atténuation partielle en v0.1 : chaque mesure minute est elle-même la médiane d'une rafale de 8 conversions. Un passage à 10–15 s d'échantillonnage intra-fenêtre (20–30 valeurs) est une option documentée, au prix du budget d'énergie — arbitrage à trancher sur mesures au banc, pas sur opinion.
