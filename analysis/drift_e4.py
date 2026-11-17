#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
drift_e4.py — Loi de dérive post-nettoyage (E4 / AC-08, DeltaFiltre).

RÔLE (Phase 7 §7-E4 points 13–14) : sur la série des bases post-nettoyage
B_n (fiche F-E4), ajuster les deux modèles concurrents de la Phase 4 (Éq. 11)

  LINÉAIRE   : B_n = B_0 + n . delta_irr
  SATURANT   : B_n = B_0 + D_max . (1 - exp(-n / tau))

et trancher par AICc selon la règle FIGÉE : l'écart ne tranche que si
|delta_AICc| >= 2 ; sinon la forme est déclarée INDÉCIDABLE. Le critère
d'affichage de l'indicateur de dérive (EF-15) n'est qu'ÉVALUÉ EN ARITHMÉTIQUE
ici : dérive cumulée corrigée > 2 x U(E) ≈ 3,2 kPa ET r_n monotone — la
correction de la dérive capteur (E6) et la monotonie de r_n restent des
conditions à vérifier HORS script ; le script le rappelle et n'active rien.

GARDES : moins de 5 cycles valides -> aucun verdict (minimum AC-08) ; le
verdict du script est exploratoire par construction (Phase 7 §7-E4 point 8 :
« loi de ce système » — 1 filtre, 1–2 eaux, 1 opérateur).

ENTRÉE : CSV d'en-tête  cycle,B_kPa  (colonne r_n facultative, utilisée pour
le test de monotonie descriptif si présente ; B_0 peut être fourni en ligne
cycle 0 ou estimé par les ajustements).
SORTIE : rapport texte. Bibliothèque standard uniquement.

INTÉGRITÉ : aucune donnée intégrée ; si le nom du fichier contient
« SYNTHETIC », le rapport est étiqueté TEST LOGICIEL.
"""

import argparse
import csv
import math
import os
import sys

SEUIL_AICC = 2.0        # règle figée Phase 7 §7-E4 point 13
SEUIL_AFFICHAGE = 3.2   # kPa = 2 x U(E) ≈ 2 x 1,6 (Phase 7 §7-E4 point 14)


def ols_multi(bases, ys):
    """Moindres carrés y ~ combinaison linéaire des vecteurs de `bases`
    (résolution des équations normales, bibliothèque standard)."""
    p = len(bases)
    n = len(ys)
    A = [[sum(bases[i][t] * bases[j][t] for t in range(n)) for j in range(p)]
         for i in range(p)]
    b = [sum(bases[i][t] * ys[t] for t in range(n)) for i in range(p)]
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for col in range(p):
        piv = max(range(col, p), key=lambda r: abs(M[r][col]))
        if abs(M[piv][col]) < 1e-14:
            return None
        M[col], M[piv] = M[piv], M[col]
        for r in range(p):
            if r != col:
                f = M[r][col] / M[col][col]
                for c in range(col, p + 1):
                    M[r][c] -= f * M[col][c]
    return [M[i][p] / M[i][i] for i in range(p)]


def sse(bases, coef, ys):
    n = len(ys)
    return sum((ys[t] - sum(c * bas[t] for c, bas in zip(coef, bases))) ** 2
               for t in range(n))


def aicc(sse_val, n, k_params):
    """AICc ; K compte les paramètres du modèle + la variance (Phase 7 :
    comparaison de modèles gaussiens — convention déclarée)."""
    if n - k_params - 1 <= 0 or sse_val <= 0:
        return float("inf")
    return (n * math.log(sse_val / n) + 2 * k_params
            + 2 * k_params * (k_params + 1) / (n - k_params - 1))


def main():
    ap = argparse.ArgumentParser(
        description="Loi de dérive post-nettoyage — E4/AC-08 DeltaFiltre "
                    "(bibliothèque standard uniquement).")
    ap.add_argument("fichier", help="CSV d'en-tête cycle,B_kPa[,r_n]")
    ap.add_argument("--derive-capteur", type=float, default=0.0,
                    help="dérive capteur mesurée en E6 sur la même période "
                         "(kPa) à retrancher de la dérive cumulée pour le "
                         "critère d'affichage (défaut : 0 — non corrigé)")
    args = ap.parse_args()
    synthetique = "SYNTHETIC" in os.path.basename(args.fichier).upper()

    cycles, bases_b, ratios = [], [], []
    with open(args.fichier, newline="", encoding="utf-8") as f:
        for l in csv.DictReader(f):
            try:
                n_c = int(float(l["cycle"]))
                b_v = float(l["B_kPa"])
            except (TypeError, ValueError, KeyError):
                continue
            cycles.append(n_c)
            bases_b.append(b_v)
            ratios.append(l.get("r_n") not in (None, "")
                          and float(l["r_n"]) or None)

    print("=" * 70)
    print("DeltaFiltre — DÉRIVE POST-NETTOYAGE (E4 / AC-08, Phase 8)")
    if synthetique:
        print("*** ENTRÉE SYNTHÉTIQUE — TEST LOGICIEL UNIQUEMENT ***")
    print("cycles valides : %d" % len(cycles))
    if len(cycles) < 5:
        print(">>> AUCUN VERDICT : moins de 5 cycles valides — minimum "
              "AC-08 non atteint (Phase 7 §7-E4 point 14).")
        return 1

    n_pts = len(cycles)
    un = [1.0] * n_pts
    # --- modèle linéaire : B = a + b.n
    coef_lin = ols_multi([un, [float(c) for c in cycles]], bases_b)
    sse_lin = sse([un, [float(c) for c in cycles]], coef_lin, bases_b)
    # --- modèle saturant : B = B0 + Dmax.(1 - exp(-n/tau)), tau par grille
    meilleur = None
    tau_candidats = [0.3 * (1.15 ** i) for i in range(80)]
    for tau in tau_candidats:
        phi = [1.0 - math.exp(-c / tau) for c in cycles]
        coef = ols_multi([un, phi], bases_b)
        if coef is None:
            continue
        s = sse([un, phi], coef, bases_b)
        if meilleur is None or s < meilleur[0]:
            meilleur = (s, tau, coef)
    sse_sat, tau_sat, coef_sat = meilleur

    K_LIN, K_SAT = 3, 4  # (2 ou 3 paramètres + variance)
    a_lin = aicc(sse_lin, n_pts, K_LIN)
    a_sat = aicc(sse_sat, n_pts, K_SAT)
    delta_aicc = a_lin - a_sat
    print("-" * 70)
    print("LINÉAIRE  : B0 = %.2f kPa, delta_irr = %.3f kPa/cycle, "
          "SSE = %.3f, AICc = %.2f"
          % (coef_lin[0], coef_lin[1], sse_lin, a_lin))
    print("SATURANT  : B0 = %.2f kPa, D_max = %.2f kPa, tau = %.2f cycles, "
          "SSE = %.3f, AICc = %.2f"
          % (coef_sat[0], coef_sat[1], tau_sat, sse_sat, a_sat))
    print("delta_AICc (linéaire - saturant) = %.2f ; règle figée : "
          "|delta| >= 2 pour trancher" % delta_aicc)
    if delta_aicc >= SEUIL_AICC:
        forme = "SATURANTE"
    elif delta_aicc <= -SEUIL_AICC:
        forme = "LINÉAIRE"
    else:
        forme = "INDÉCIDABLE"
    print(">>> FORME DE LA DÉRIVE : %s" % forme)
    if forme == "LINÉAIRE":
        print("    delta_irr = %.3f kPa/cycle (pente du modèle retenu)"
              % coef_lin[1])

    # --- critère d'affichage (arithmétique seulement — voir en-tête)
    derive_cum = bases_b[-1] - bases_b[0]
    derive_corr = derive_cum - args.derive_capteur
    print("-" * 70)
    print("critère d'affichage EF-15 (évaluation arithmétique, Phase 7 "
          "§7-E4-14) :")
    print("  dérive cumulée brute = %.2f kPa ; corrigée capteur = %.2f kPa "
          "(correction fournie : %.2f) ; seuil 2 x U(E) = %.1f kPa -> %s"
          % (derive_cum, derive_corr, args.derive_capteur, SEUIL_AFFICHAGE,
             "dépassé" if derive_corr > SEUIL_AFFICHAGE else "NON dépassé"))
    r_valides = [r for r in ratios if r is not None]
    if len(r_valides) >= 3:
        diffs = [r_valides[i + 1] - r_valides[i]
                 for i in range(len(r_valides) - 1)]
        neg = sum(1 for d in diffs if d < 0)
        print("  r_n : %d/%d différences successives négatives (tendance "
              "monotone décroissante : %s — descriptif, Phase 7)"
              % (neg, len(diffs),
                 "oui" if neg == len(diffs) else "non stricte"))
    else:
        print("  r_n : colonne absente ou incomplète — monotonie non "
              "évaluée.")
    print("  RAPPEL : l'activation du seuil d'affichage exige EN PLUS la "
          "dérive capteur d'E6 et la monotonie de r_n vérifiées sur "
          "données réelles ; ce script n'active rien.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
