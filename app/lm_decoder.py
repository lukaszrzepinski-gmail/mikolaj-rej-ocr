"""Preserved Diariusz CTC decoder functions; no training/evaluation corpus."""
def beam_lm(probs, alfabet, lm, alpha, beta, beam, prog=1e-3):
    """CTC prefix beam search; LM znakowy (KenLM, tokeny = znaki, spacja = ▁) dodaje alpha*ln P(znak|kontekst) + beta za znak."""
    import kenlm
    T = probs.shape[1]
    LN10 = math.log(10)
    # stan: prefiks (krotka etykiet) -> (log p_b, log p_nb, lm_state, lm_score, ostatni_tekst)
    start = kenlm.State(); lm.BeginSentenceWrite(start) if lm is not None else None
    beams = {(): (0.0, -math.inf, start, 0.0)}
    lse = lambda a, b: a if b == -math.inf else (b if a == -math.inf else max(a, b) + math.log1p(math.exp(-abs(a - b))))
    lp = np.log(np.clip(probs.astype(np.float32), 1e-12, 1))
    for t in range(T):
        kol = lp[:, t]
        kand = [c for c in np.nonzero(kol > math.log(prog))[0]]
        nowe = defaultdict(lambda: [-math.inf, -math.inf, None, 0.0])
        for pref, (pb, pnb, st, lms) in beams.items():
            ptot = lse(pb, pnb)
            for c in kand:
                p = kol[c]
                if c == 0:
                    n = nowe[pref]; n[0] = lse(n[0], ptot + p); n[2] = st; n[3] = lms
                    continue
                last = pref[-1] if pref else None
                npref = pref + (c,)
                if c == last:
                    n = nowe[pref]; n[1] = lse(n[1], pnb + p); n[2] = st; n[3] = lms   # powtorzenie bez blanku = ten sam znak
                    n2 = nowe[npref]
                    if n2[2] is None:
                        s2, sc = lm_krok(lm, st, alfabet.get(c, ""), alpha, beta, LN10)
                        n2[2] = s2; n2[3] = lms + sc
                    n2[1] = lse(n2[1], pb + p)
                else:
                    n2 = nowe[npref]
                    if n2[2] is None:
                        s2, sc = lm_krok(lm, st, alfabet.get(c, ""), alpha, beta, LN10)
                        n2[2] = s2; n2[3] = lms + sc
                    n2[1] = lse(n2[1], ptot + p)
        beams = dict(sorted(((k, tuple(v)) for k, v in nowe.items()), key=lambda kv: -(lse(kv[1][0], kv[1][1]) + kv[1][3]))[:beam])
    best = max(beams.items(), key=lambda kv: lse(kv[1][0], kv[1][1]) + kv[1][3])[0]
    return "".join(alfabet.get(c, "") for c in best)

def lm_krok(lm, st, s, alpha, beta, LN10):
    import kenlm
    if lm is None or alpha == 0:
        return st, beta * len(s)
    sc = 0.0; cur = st
    for ch in unicodedata.normalize("NFD", s):
        tok = SP if ch == " " else ch
        nst = kenlm.State()
        sc += lm.BaseScore(cur, tok, nst) * LN10
        cur = nst
    return cur, alpha * sc + beta * len(s)
