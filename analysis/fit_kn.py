#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fit_kn.py — Ajustement hors ligne (k, n) de la loi dP = k.Q^n (E1, DeltaFiltre).

RÔLE (Phase 7 §4-E1 points 9 et 13) : ajuster, sur les couples (Q, dP) mesurés
VOLUMÉTRIQUEMENT en eau claire (référence indépendante du produit), la loi de
filtre dP = k.Q^n par régression OLS sur ln dP = ln k + n.ln Q ; rapporter
l'IC 95 % sur n, les résidus (recherche de courbure), et comparer — si on les
fournit — les (k, n, Q_ref) de l'étalonnage EMBARQUÉ (EF-08) à l'ajustement
hors ligne (critère E1 : écart <= 10 %).

GARDES DE REFUS (miroir du firmware, Phase 6 §3.3 — jamais de fit forcé) :
  * moins de 2 points exploitables            -> REFUS ;
  * Q ou dP non strictement positifs          -> point exclu et compté, REFUS
                                                 s'il ne reste rien de valide ;
  * dispersion des débits insuffisante : Qmax/Qmin < 1,20 -> REFUS (points
    quasi identiques : la pente n'est pas identifiable) ;
  * n ajusté hors de l'enveloppe [0,5 ; 2,5]  -> REFUS (fit non accepté comme
    étalonnage ; les valeurs sont quand même imprimées pour diagnostic).
Le design d'E1 vise 5 paliers x 3 répétitions x montée/descente ; le script
signale tout effectif inférieur à 5 points distincts comme sous le design.

ENTRÉE : CSV d'en-tête  Q_L_min,dP_kPa  (colonnes supplémentaires ignorées ;
une ligne par mesure, répétitions incluses).
SORTIE : rapport texte. Bibliothèque standard uniquement.

INTÉGRITÉ : aucune donnée intégrée ; si le nom du fichier contient
« SYNTHETIC », le rapport est étiqueté TEST LOGICIEL.
"""

import argparse
import csv
import math
import os
import sys

# t de Student bilatéral 95 % selon les degrés de liberté (table standard).
T95 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365,
       8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 13: 2.160,
       14: 2.145, 15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093,
       20: 2.086, 21: 2.080, 22: 2.074, 23: 2.069, 24: 2.064, 25: 2.060,
       26: 2.056, 27: 2.052, 28: 2.048, 29: 2.045, 30: 2.042}


def t95(df):
    return T95.get(df, 1.96)


def ols(xs, ys):
    """Régression y = a + b.x. Retourne (a, b, se_b, residus, r2)."""
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    b = sxy / sxx
    a = my - b * mx
    residus = [y - (a + b * x) for x, y in zip(xs, ys)]
    sse = sum(r * r for r in residus)
    sst = sum((y - my) ** 2 for y in ys)
    r2 = 1.0 - sse / sst if sst > 0 else float("nan")
    if n > 2 and sxx > 0:
        se_b = math.sqrt((sse / (n - 2)) / sxx)
    else:
        se_b = float("nan")
    return a, b, se_b, residus, r2


def resoudre3(A, b):
    """Résout un système 3x3 (élimination de Gauss, pivot partiel)."""
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for col in range(3):
        piv = max(range(col, 3), key=lambda r: abs(M[r][col]))
        if abs(M[piv][col]) < 1e-14:
            return None
        M[col], M[piv] = M[piv], M[col]
        for r in range(3):
            if r != col:
                f = M[r][col] / M[col][col]
                for c in range(col, 4):
                    M[r][c] -= f * M[col][c]
    return [M[i][3] / M[i][i] for i in range(3)]


def fit_quadratique(xs, ys):
    """Ajuste y = a + b.x + c.x^2 ; retourne (c, r2_quad) ou None."""
    n = len(xs)
    sx = [sum(x ** p for x in xs) for p in range(5)]
    sy = [sum(y * x ** p for x, y in zip(xs, ys)) for p in range(3)]
    A = [[sx[p + q] for q in range(3)] for p in range(3)]
    sol = resoudre3(A, sy)
    if sol is None:
        return None
    a, b, c = sol
    my = sum(ys) / n
    sse = sum((y - (a + b * x + c * x * x)) ** 2 for x, y in zip(xs, ys))
    sst = sum((y - my) ** 2 for y in ys)
    r2 = 1.0 - sse / sst if sst > 0 else float("nan")
    return c, r2


def main():
    ap = argparse.ArgumentParser(
        description="Ajustement (k, n) hors ligne — E1 DeltaFiltre "
                    "(bibliothèque standard uniquement).")
    ap.add_argument("fichier", help="CSV d'en-tête Q_L_min,dP_kPa")
    ap.add_argument("--embarque", nargs=3, type=float, metavar=("K", "N",
                    "QREF"), default=None,
                    help="valeurs (k, n, Q_ref) de l'étalonnage embarqué à "
                         "comparer (critère E1 : écart <= 10 %)")
    args = ap.parse_args()
    synthetique = "SYNTHETIC" in os.path.basename(args.fichier).upper()

    points, exclus = [], 0
    with open(args.fichier, newline="", encoding="utf-8") as f:
        for l in csv.DictReader(f):
            try:
                q = float(l["Q_L_min"])
                dp = float(l["dP_kPa"])
            except (TypeError, ValueError, KeyError):
                exclus += 1
                continue
            if q <= 0 or dp <= 0:
                exclus += 1
                continue
            points.append((q, dp))

    print("=" * 70)
    print("DeltaFiltre — AJUSTEMENT (k, n) HORS LIGNE (E1, Phase 8)")
    if synthetique:
        print("*** ENTRÉE SYNTHÉTIQUE — TEST LOGICIEL UNIQUEMENT ***")
    print("points exploitables : %d (exclus : %d)" % (len(points), exclus))

    if len(points) < 2:
        print(">>> REFUS : moins de 2 points exploitables — aucun fit "
              "(garde Phase 6 §3.3).")
        return 1
    qs = [q for q, _ in points]
    if max(qs) / min(qs) < 1.20:
        print(">>> REFUS : dispersion des débits insuffisante "
              "(Qmax/Qmin = %.3f < 1,20) — points quasi identiques, pente "
              "non identifiable (garde Phase 6 §3.3)."
              % (max(qs) / min(qs)))
        return 1
    if len(set(qs)) < 5:
        print("note : %d paliers de débit distincts (< 5 du design E1) — "
              "caractérisation réduite, à déclarer." % len(set(qs)))

    xs = [math.log(q) for q, _ in points]
    ys = [math.log(dp) for _, dp in points]
    a, n_exp, se_n, residus, r2 = ols(xs, ys)
    k = math.exp(a)
    df = len(points) - 2
    ic_n = None
    if df >= 1 and se_n == se_n:
        demi = t95(df) * se_n
        ic_n = (n_exp - demi, n_exp + demi)
    print("-" * 70)
    print("fit log-log : n = %.3f%s ; k = %.4f kPa/(L/min)^n ; R² = %.4f"
          % (n_exp, "" if ic_n is None else
             " (IC 95 %% : %.3f – %.3f)" % ic_n, k, r2))
    print("résidus ln dP : max |r| = %.4f ; signes : %s"
          % (max(abs(r) for r in residus),
             "".join("+" if r >= 0 else "-" for r in residus)))
    quad = fit_quadratique(xs, ys)
    if quad is not None:
        c, r2q = quad
        gain = r2q - r2
        print("courbure : terme quadratique c = %.3f ; gain de R² = %.4f %s"
              % (c, gain,
                 "-> COURBURE POSSIBLE (la loi puissance serait à "
                 "re discuter)" if gain > 0.02 else "-> pas de courbure "
                 "manifeste"))
    if not (0.5 <= n_exp <= 2.5):
        print(">>> REFUS comme étalonnage : n = %.3f hors de l'enveloppe "
              "figée [0,5 ; 2,5] (garde Phase 6 §3.3) — fit imprimé "
              "ci-dessus à titre de diagnostic seulement." % n_exp)
        return 1
    print("bornes physiques Phase 4 (n dans [1 ; 2]) : %s"
          % ("IC 95 % inclus dans [1 ; 2]" if ic_n and ic_n[0] >= 1.0
             and ic_n[1] <= 2.0 else
             "IC non inclus dans [1 ; 2] — écart à expliquer (critère E1-a) "
             "ou à rapporter tel quel"))
    if args.embarque:
        k_e, n_e, qref_e = args.embarque
        print("-" * 70)
        print("comparaison embarqué vs hors ligne (critère E1-b : <= 10 %) :")
        for nom, emb, ref in (("k", k_e, k), ("n", n_e, n_exp)):
            ecart = abs(emb - ref) / ref * 100.0
            print("  %s : embarqué %.4f, hors ligne %.4f -> écart %.1f %% %s"
                  % (nom, emb, ref, ecart,
                     "OK" if ecart <= 10.0 else "ÉCHEC du critère"))
        print("  Q_ref embarqué : %.1f L/min (pas d'équivalent hors ligne "
              "direct ; Q_ref est le point « régime habituel » désigné)"
              % qref_e)
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
