# -*- coding: utf-8 -*-
"""Scores the site's hand-written Korean against the humanize-korean taxonomy.

    git clone --depth 1 https://github.com/epoko77-ai/im-not-ai
    python tools/diagnose.py --skill ../im-not-ai

Reads the prose back out of the built pages rather than out of build.py, so what is
measured is what a reader gets. Two numbers matter more than the rest:

  C-11  connective ending followed by a comma. The single strongest separator in the
        whole scheme (human 4.10% vs AI 19.83% on the KatFish essays). This site once
        scored 60% - three times worse than the AI baseline - because "세우고, 나누고,"
        felt like English comma habit and nobody had measured it.

  E-2   sentence-ending uniformity. 합니다체 ends every sentence in 다, so a whole page
        of it is one long run by construction; the fix was 평서체 plus the odd noun or
        question ending, not a shorter page.
"""
import argparse
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(HERE, "..", "docs")

PAGES = ["index.html", "races.html", "buildings.html", "units.html",
         "research.html", "controls.html"]


def prose():
    """The sentences a reader actually reads: leads, subs, steps, paragraphs."""
    out = []
    for name in PAGES:
        p = os.path.join(DOCS, name)
        if not os.path.exists(p):
            continue
        s = io.open(p, encoding="utf-8").read()
        s = re.sub(r"<script.*?</script>", "", s, flags=re.S)
        blocks = re.findall(r'<p class="(?:lead|sub)">(.*?)</p>', s, re.S)
        blocks += re.findall(r'<div>\s*<h2>.*?</h2>(.*?)</div>', s, re.S)
        blocks += re.findall(r'<li><b>.*?</b><span>(.*?)</span></li>', s, re.S)
        for b in blocks:
            t = re.sub(r"<[^>]+>", " ", b)
            t = t.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
            t = re.sub(r"\s+", " ", t).strip()
            if len(t) > 8:
                out.append(t)
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skill", default=os.path.join(HERE, "..", "..", "im-not-ai"),
                    help="checkout of github.com/epoko77-ai/im-not-ai")
    a = ap.parse_args()

    ref = os.path.join(a.skill, "skills", "humanize-korean", "references")
    if not os.path.isdir(ref):
        print("skill checkout not found: %s" % ref)
        return 2
    sys.path.insert(0, ref)
    import metrics as m1
    import metrics_v2 as m2

    text = prose()
    if not text:
        print("no prose found - run build.py first")
        return 2

    rows = [
        ("C-11 연결어미 뒤 쉼표", "%.3f" % m1.ending_comma_rate(text), "인간 0.041 · AI 0.198"),
        ("C-12 쉼표 포함률", "%.3f" % m1.comma_inclusion_rate(text), ""),
        ("C-8  대구", m2.antithesis_count(text), "사람 코퍼스 0건"),
        ("D-1  결산 lexicon", m1.conclusion_pivot_count(text), "3 초과면 가산"),
        ("E-2  '다' 연속 4+ 구간", m2.da_streak_rate(text), "0 이 목표"),
        ("E-2  종결어미 다양도", "%.3f" % m2.ending_diversity(text), "높을수록 좋음"),
        ("A-8  이중 피동", m2.double_passive_count(text), ""),
        ("A-9  '에 의해' 피동", m2.by_passive_count(text), ""),
        ("A-7  have/make 직역", m2.have_make_literal_count(text), ""),
        ("A-15 무정물 주어율", "%.3f" % m2.inanimate_subject_rate(text), ""),
        ("A-19 이중 조사", m2.double_particle_count(text), ""),
        ("     진행형 '고 있다'", "%.3f" % m2.progressive_aspect_rate(text), "0.5 초과면 가산"),
        ("     어휘 다양도 TTR", "%.3f" % m2.lexical_diversity_ttr(text), ""),
    ]
    print("문구 %d자\n" % len(text))
    for name, v, note in rows:
        print("  %-24s %-8s %s" % (name, v, note))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
