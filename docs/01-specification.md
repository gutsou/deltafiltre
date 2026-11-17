# Spécification produit (condensé — Phase 5 du dossier)

**Description neutre :** enregistreur autonome de pression différentielle, à alarme relative à une base propre mesurée, destiné à la surveillance des filtres de tête **manuels existants** des petites installations d'irrigation goutte-à-goutte. Il mesure les pressions amont et aval, calcule ΔP, la compare — dans des conditions de débit et de température documentées — à la perte de charge du même filtre propre mesurée à la mise en service, et signale le moment où un nettoyage est justifié. Il journalise la série temporelle complète, suit l'évolution de la base après chaque nettoyage, et intègre un contrôle de zéro par égalisation des prises. **Autonome** (batterie, basse tension), **hors ligne**, **indépendant de marque**, **sans actionnement**.

## Exigences fonctionnelles (extraits normatifs)

- **EF-01/02** — Deux transmetteurs relatifs compatibles eau (membrane inox), gamme nominale **0–600 kPa** (variante 0–1 MPa si la pression de ligne l'exige), classe **≤ ±1 % PE**, **±0,5 % préféré**. Les capteurs « board-mount » (air sec/gaz) sont **exclus** de la chaîne principale.
- **EF-03** — Acquisition par **CAN externe 16 bits** (type ADS1115) ; CAN interne ESP32 **exclu** ; mesure **ratiométrique** (le rail d'excitation est mesuré et divise la lecture).
- **EF-04** — Échantillonnage ≥ **1 mesure/minute** par voie ; agrégat journalisé = **médiane sur 5 minutes** de P_amont, P_aval, ΔP, T_eau.
- **EF-06** — Tout enregistrement est **horodaté par RTC** ; horodatages monotones.
- **EF-08** — Mise en service : mesure volumétrique (récipient gradué + chronomètre) d'au moins **2 couples (Q, ΔP propre)** (3 recommandés) → ajustement (k, n, Q_ref).
- **EF-10/11** — Base propre **B_0** capturée à la mise en service (jamais de valeur d'usine) ; règle d'alarme **exclusivement relative** : E = ΔP_norm − B_n, δ défaut **20 kPa** (réglable 20–40), persistance **3 fenêtres valides**, hystérésis **5 kPa**.
- **EF-12** — **Aucun mode à seuil absolu fixe** embarqué ; le seuil 0,5 bar n'existe que comme témoin d'analyse hors ligne.
- **EF-13** — Alarme locale : voyant + buzzer acquittable ; l'état persiste tant que E reste au-dessus du seuil d'effacement.
- **EF-15** — Indicateur de dérive post-nettoyage formulé partout comme **« indicateur en cours de validation »**, jamais comme diagnostic ; seuil d'affichage désactivé par défaut en v1.
- **EF-17/18** — Contrôle de zéro par égalisation intégré ; tolérance par défaut **2 kPa** ; au-delà : avertissement « dérive capteur suspectée » distinct, données marquées « zéro non vérifié ».
- **EF-19** — Journalisation continue hors ligne sur **carte SD**, série complète (pas seulement les événements), format texte documenté (voir `04-data-format.md`).
- **EF-20** — Affichage local minimal : ΔP courante, E courant, état, date du dernier contrôle de zéro.
- **EF-22** — **Alarme seule** : aucune sortie d'actionnement (ni relais vanne, ni commande pompe, ni rétrolavage). Toute évolution vers l'actionnement sort du périmètre v1.

## Exigences non fonctionnelles (extraits)

- **ENF-01** — Autonomie cible **≥ 3 mois** (budget calculé ≈ 130 jours sous conditions — voir `02-architecture.md`).
- **ENF-02** — Boîtier fermé, objectif **IP65** par construction (non certifié).
- **ENF-04** — Plafond de coût initial 700 MAD **non tenu** : coût matière réel du design ≈ **1 445 MAD**, dépassement explicité poste par poste (`03-bom.md`).
- **ENF-05** — Maintenabilité : pièces standard remplaçables sans retour fabricant ; le remplacement d'un transmetteur impose contrôle de zéro + re-capture de base (l'ancienne base n'est plus comparable — changement d'instrument, journalisé).

## Limites d'usage déclarées

Filtres de tête manuels d'irrigation goutte-à-goutte uniquement (tamis, disques, sable/média). Sur eaux très chargées, l'alarme sera correcte mais la fréquence de nettoyage peut devenir impraticable (< 0,5 h documenté) — limite d'usage, pas défaut de mesure. Sur eau propre, l'alarme peut ne jamais se déclencher sur une saison — à juste titre. Le produit ne promet **aucun délai de détection universel**.
