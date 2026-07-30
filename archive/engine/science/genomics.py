# deep/science/genomics.py — Sequence Analysis (Bible Section 8.1)
"""DNA/RNA/protein sequence analysis: alignment, k-mers, CpG islands,
transcription/translation, de Bruijn assembly. Pure-Python core; Biopython
optional."""
from __future__ import annotations

import math
from collections import Counter

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None

try:
    import networkx as nx
    NX = True
except Exception:  # pragma: no cover
    NX = False

CODON_TABLE = {
    'TTT': 'F', 'TTC': 'F', 'TTA': 'L', 'TTG': 'L', 'CTT': 'L', 'CTC': 'L', 'CTA': 'L',
    'CTG': 'L', 'ATT': 'I', 'ATC': 'I', 'ATA': 'I', 'ATG': 'M', 'GTT': 'V', 'GTC': 'V',
    'GTA': 'V', 'GTG': 'V', 'TCT': 'S', 'TCC': 'S', 'TCA': 'S', 'TCG': 'S', 'CCT': 'P',
    'CCC': 'P', 'CCA': 'P', 'CCG': 'P', 'ACT': 'T', 'ACC': 'T', 'ACA': 'T', 'ACG': 'T',
    'GCT': 'A', 'GCC': 'A', 'GCA': 'A', 'GCG': 'A', 'TAT': 'Y', 'TAC': 'Y', 'TAA': '*',
    'TAG': '*', 'CAT': 'H', 'CAC': 'H', 'CAA': 'Q', 'CAG': 'Q', 'AAT': 'N', 'AAC': 'N',
    'AAA': 'K', 'AAG': 'K', 'GAT': 'D', 'GAC': 'D', 'GAA': 'E', 'GAG': 'E', 'TGT': 'C',
    'TGC': 'C', 'TGA': '*', 'TGG': 'W', 'CGT': 'R', 'CGC': 'R', 'CGA': 'R', 'CGG': 'R',
    'AGT': 'S', 'AGC': 'S', 'AGA': 'R', 'AGG': 'R', 'GGT': 'G', 'GGC': 'G', 'GGA': 'G',
    'GGG': 'G',
}
_COMPLEMENT = str.maketrans("ACGTacgt", "TGCAtgca")


class GenomicsEngine:
    def __init__(self, config=None):
        self.config = config

    # ── basic sequence ops ──────────────────────────────────────────
    def gc_content(self, seq: str) -> dict:
        seq = seq.upper()
        gc = sum(seq.count(b) for b in "GC")
        pct = 100 * gc / len(seq) if seq else 0
        return {"gc_content": pct, "result": pct,
                "verbal": f"GC content is {pct:.2f}% over {len(seq)} bases."}

    def reverse_complement(self, seq: str) -> dict:
        rc = seq.upper().translate(_COMPLEMENT)[::-1]
        return {"reverse_complement": rc, "result": rc,
                "verbal": f"Reverse complement: {rc[:60]}{'…' if len(rc) > 60 else ''}"}

    def transcribe(self, dna: str) -> dict:
        rna = dna.upper().replace("T", "U")
        return {"rna": rna, "result": rna, "verbal": f"Transcribed to RNA: {rna[:60]}"}

    def translate(self, dna: str) -> dict:
        seq = dna.upper().replace("U", "T")
        protein = "".join(CODON_TABLE.get(seq[i:i+3], "X")
                          for i in range(0, len(seq) - 2, 3))
        return {"protein": protein, "result": protein,
                "verbal": f"Translated to protein ({len(protein)} aa): {protein[:60]}"}

    # ── 8.1 alignment (scratch DP) ──────────────────────────────────
    def needleman_wunsch(self, seq1, seq2, match=1, mismatch=-1, gap=-2) -> dict:
        n, m = len(seq1), len(seq2)
        D = [[0] * (m + 1) for _ in range(n + 1)]
        for i in range(n + 1):
            D[i][0] = i * gap
        for j in range(m + 1):
            D[0][j] = j * gap
        for i in range(1, n + 1):
            for j in range(1, m + 1):
                s = match if seq1[i-1] == seq2[j-1] else mismatch
                D[i][j] = max(D[i-1][j-1] + s, D[i-1][j] + gap, D[i][j-1] + gap)
        # traceback
        a1, a2 = "", ""
        i, j = n, m
        while i > 0 or j > 0:
            if i > 0 and j > 0 and D[i][j] == D[i-1][j-1] + (match if seq1[i-1] == seq2[j-1] else mismatch):
                a1, a2 = seq1[i-1] + a1, seq2[j-1] + a2; i -= 1; j -= 1
            elif i > 0 and D[i][j] == D[i-1][j] + gap:
                a1, a2 = seq1[i-1] + a1, "-" + a2; i -= 1
            else:
                a1, a2 = "-" + a1, seq2[j-1] + a2; j -= 1
        ident = sum(c1 == c2 for c1, c2 in zip(a1, a2))
        return {"alignment": (a1, a2), "score": D[n][m], "identity": ident,
                "result": D[n][m],
                "verbal": f"Global alignment score {D[n][m]}; {ident}/{len(a1)} identical positions."}

    def smith_waterman(self, seq1, seq2, match=2, mismatch=-1, gap=-2) -> dict:
        n, m = len(seq1), len(seq2)
        H = [[0] * (m + 1) for _ in range(n + 1)]
        best, bi, bj = 0, 0, 0
        for i in range(1, n + 1):
            for j in range(1, m + 1):
                s = match if seq1[i-1] == seq2[j-1] else mismatch
                H[i][j] = max(0, H[i-1][j-1] + s, H[i-1][j] + gap, H[i][j-1] + gap)
                if H[i][j] > best:
                    best, bi, bj = H[i][j], i, j
        return {"score": best, "end": (bi, bj), "result": best,
                "verbal": f"Best local alignment score {best}."}

    # ── 8.1 k-mers / CpG ────────────────────────────────────────────
    def kmer_analysis(self, sequence, k=3) -> dict:
        seq = sequence.upper()
        kmers = Counter(seq[i:i+k] for i in range(len(seq) - k + 1))
        total = sum(kmers.values())
        entropy = -sum((c/total) * math.log2(c/total) for c in kmers.values()) if total else 0
        top = kmers.most_common(5)
        return {"kmer_counts": dict(kmers), "entropy": entropy, "overrepresented": top,
                "result": dict(kmers),
                "verbal": f"{len(kmers)} distinct {k}-mers, Shannon entropy {entropy:.3f} bits; "
                          f"most common: {top[0][0]} ({top[0][1]}×)." if top else "empty sequence."}

    def cpg_island_detection(self, dna_seq, window=200, threshold=0.6) -> dict:
        seq = dna_seq.upper()
        islands = []
        for start in range(0, max(1, len(seq) - window + 1), window // 2 or 1):
            w = seq[start:start + window]
            if len(w) < window // 2:
                continue
            gc = sum(w.count(b) for b in "GC") / len(w)
            obs_cpg = w.count("CG")
            exp_cpg = (w.count("C") * w.count("G")) / len(w) if len(w) else 0
            oe = obs_cpg / exp_cpg if exp_cpg else 0
            if gc > 0.5 and oe > threshold:
                islands.append({"start": start, "end": start + len(w),
                                "GC_content": round(gc, 3), "CpG_OE": round(oe, 3)})
        return {"islands": islands, "result": islands,
                "verbal": f"Found {len(islands)} candidate CpG island window(s)."}

    # ── 8.1 de Bruijn assembly ──────────────────────────────────────
    def debruijn_assembly(self, reads, k=4) -> dict:
        if not NX:
            return {"result": None, "verbal": "networkx not available, sir."}
        G = nx.MultiDiGraph()
        for read in reads:
            for i in range(len(read) - k + 1):
                kmer = read[i:i+k]
                G.add_edge(kmer[:-1], kmer[1:])
        contigs = []
        try:
            for path in nx.weakly_connected_components(G):
                sub = G.subgraph(path)
                if nx.has_eulerian_path(sub):
                    euler = list(nx.eulerian_path(sub))
                    if euler:
                        contig = euler[0][0] + "".join(e[1][-1] for e in euler)
                        contigs.append(contig)
        except Exception:
            pass
        return {"contigs": contigs, "n_nodes": G.number_of_nodes(), "result": contigs,
                "verbal": f"de Bruijn graph: {G.number_of_nodes()} nodes, "
                          f"{len(contigs)} contig(s) assembled."}

    def multiple_sequence_alignment(self, sequences) -> dict:
        """Center-star progressive MSA built on pairwise Needleman-Wunsch."""
        if len(sequences) < 2:
            return {"result": None, "verbal": "Give me at least two sequences, sir."}
        scores = [sum(self.needleman_wunsch(s, t)["score"] for t in sequences)
                  for s in sequences]
        center = int(np.argmax(scores)) if np is not None else 0
        aligned = [sequences[center]]
        for i, s in enumerate(sequences):
            if i == center:
                continue
            aligned.append(self.needleman_wunsch(sequences[center], s)["alignment"][1])
        L = max(len(a) for a in aligned)
        aligned = [a.ljust(L, "-") for a in aligned]
        consensus = "".join(Counter(a[c] for a in aligned).most_common(1)[0][0]
                            for c in range(L))
        cons = [max(Counter(a[c] for a in aligned).values()) / len(aligned) for c in range(L)]
        return {"alignment": aligned, "consensus": consensus.replace("-", ""),
                "conservation": cons, "result": consensus,
                "verbal": f"Aligned {len(sequences)} sequences (center-star); "
                          f"mean column conservation {100*np.mean(cons):.0f}%."}

    def phylogenetic_tree(self, sequences, names=None) -> dict:
        """p-distance matrix + UPGMA → Newick string."""
        n = len(sequences); names = names or [f"S{i+1}" for i in range(n)]

        def pdist(a, b):
            al = self.needleman_wunsch(a, b)["alignment"]
            return sum(x != y for x, y in zip(*al)) / max(1, len(al[0]))
        D = [[pdist(sequences[i], sequences[j]) for j in range(n)] for i in range(n)]
        clusters = {i: (names[i], 1) for i in range(n)}
        dist = {(i, j): D[i][j] for i in range(n) for j in range(i+1, n)}
        nxt = n
        while len(clusters) > 1:
            (i, j), dmin = min(dist.items(), key=lambda kv: kv[1])
            (ni, si), (nj, sj) = clusters[i], clusters[j]
            new_id = nxt; nxt += 1
            clusters[new_id] = (f"({ni}:{dmin/2:.3f},{nj}:{dmin/2:.3f})", si + sj)
            for k in list(clusters):
                if k in (i, j, new_id):
                    continue
                dik = dist.get((min(i, k), max(i, k)), 0); djk = dist.get((min(j, k), max(j, k)), 0)
                dist[(min(new_id, k), max(new_id, k))] = (dik*si + djk*sj) / (si+sj)
            del clusters[i]; del clusters[j]
            dist = {k: v for k, v in dist.items() if i not in k and j not in k}
        newick = list(clusters.values())[0][0] + ";"
        return {"newick": newick, "distance_matrix": D, "result": newick,
                "verbal": f"Built UPGMA phylogenetic tree of {n} taxa: {newick}"}

    def test(self) -> None:
        assert abs(self.gc_content("GGCC")["gc_content"] - 100.0) < 1e-9
        assert self.translate("ATGGCC")["protein"] == "MA"
        assert self.reverse_complement("ATGC")["reverse_complement"] == "GCAT"
        nw = self.needleman_wunsch("GATTACA", "GCATGCU")
        assert "score" in nw
        msa = self.multiple_sequence_alignment(["ACGTACGT", "ACGAACGT", "ACGTACGA"])
        assert len(msa["alignment"]) == 3
        tree = self.phylogenetic_tree(["ACGTACGT", "ACGAACGT", "TTTTACGT"])
        assert tree["newick"].endswith(";")
        print("genomics.GenomicsEngine: OK (incl. MSA, UPGMA phylogeny)")


_engine = GenomicsEngine()


def analyze(text: str) -> dict:
    import re
    m = re.search(r"\b([ACGTUacgtu]{4,})\b", text)
    if not m:
        return {"result": None, "verbal": "Give me a DNA/RNA sequence, sir."}
    seq = m.group(1)
    if "translate" in text.lower():
        return _engine.translate(seq)
    if "complement" in text.lower():
        return _engine.reverse_complement(seq)
    return _engine.gc_content(seq)


def test() -> None:
    GenomicsEngine().test()


if __name__ == "__main__":
    test()
