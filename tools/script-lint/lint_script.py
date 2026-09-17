#!/usr/bin/env python3
"""Count the prose tells in a script's narration and quote every hit.

    python tools/script-lint/lint_script.py content/<series>/<slug>/claude/script.md [--english british|american]

Reads the narration only (everything before a "## Handoff" heading; headings,
tables and bullets skipped). Counts are evidence for the scorer, not verdicts:
a deliberate fragment run or an earned "kind of" survives a human read. Em dashes
are the one hard bar: exit 1 if any remain. Stdlib only.
"""

import re, sys, statistics

EM = "—"
FLIP = re.compile(
    r"\b(?:not just|not only|not merely|isn't just|wasn't just|isn't a|wasn't a|is not a|was not a|doesn't|didn't|never)\b"
    r"[^.?!]{0,80}\.\s+(?:It's|It is|That's|That is|This is|It was|They are|He is|She is)\b"
    r"|\b(?:not|never)\b[^.?!]{0,60},\s*(?:but|it's|it is)\b", re.I)
QA = re.compile(r"\?\s+(?:[A-Z][^.!?\s]*)(?:\s+[^.!?\s]+){0,4}\.")
SUMTAG = re.compile(r"\bThat(?:'s| is) the (?:difference|mechanism|point|deal|trick|whole|part|price|cost|lesson|catch)\b"
                    r"|\bonly made it official\b|\bthat(?:'s| is) the whole (?:story|game)\b", re.I)
CHARQUOTE = re.compile(r"\b(?:what sounded like|what looked like|with what passed for)\b[^.]{0,40}:", re.I)
MOVES = ["here's the thing", "here's why", "here's where it gets", "here's the kicker", "here's the part", "but get this",
         "and get this", "here's the wild part", "let me walk you through", "let me break this down", "let me be honest",
         "run the numbers", "do the math", "add it up", "which brings us to", "before we get into", "buckle up",
         "strap in", "let's dive in", "sit with that", "let that sink in", "make no mistake",
         "what you need to understand", "what makes this different", "the reason goes deeper"]
WORDS = ["delv", "furthermore", "moreover", "additionally", "crucial", "robust", "unprecedented", "leverag", "foster",
         "seamless", "elevat", "navigat", "game-chang", "paradigm", "tapestry", "landscape", "realm", "testament",
         "underscore", "pivotal", "groundbreaking", "transformative", "multifaceted", "intricate", "nuanced", "myriad",
         "plethora", "embark", "journey", "unlock", "harness", "empower", "resonat", "vibrant", "bustling", "nestled",
         "meticulous", "utiliz", "facilitat"]
PHRASES = ["a testament to", "the landscape of", "in today's world", "in our modern era", "in the ever-evolving",
           "it is important to note", "it's worth noting", "it's important to understand", "in conclusion",
           "to summarize", "in summary", "as we've discussed", "at the end of the day", "plays a crucial role",
           "stands as a", "serves as a", "is a reminder that", "the quiet ", "what amounts to",
           "in what can only be described as", "some say", "many experts believe", "it's been reported"]
HEDGES = ["kind of", "sort of", "very ", "really ", "truly ", "perhaps", "arguably", "absolutely", "incredibly",
          "pretty much", "somewhat"]
AMERICAN = (r"\b(colou?r(?<!colour)s?|colored|honor(?:s|ed)?|favor(?:s|ed|ite)?|labor|neighbor(?:s|hood)?|armor|harbor|"
            r"center(?:s|ed)?|meters?|theater|gray|gotten|travel(?:ed|ing)|jewelry|defense|offense|pretense|skeptic(?:al|ism)?|"
            r"catalog|plow|mold|smolder|aluminum|math|toward|apartment|elevator|sidewalk|trash|garbage|mom|diaper|faucet|"
            r"movies?|candy|soccer|vacation|cookies?|gas station|parking lot|railroad|fall(?= of \d)|"
            r"[a-z]{3,}iz(?:e[sd]?|ing|ation))\b")
# ear checks: constructions that pass every band above and still fail when spoken (Krays, 2026-09-16)
YOU = re.compile(r"\byou(?:r|'re|'ve|'ll)?\b", re.I)
REFERENT = re.compile(r"\b(?:that much|half that|those things|the one in|that number|none of those|either of them)\b", re.I)
NUMWORD = re.compile(r"\b(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|"
                     r"sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|"
                     r"hundred|thousand|million)\b", re.I)
ABSTRACT = re.compile(r"\b(?:thing|things|something|anything|nothing|everything|everybody|anybody|nobody|somebody|"
                      r"whole|part|point|means|matters|worth)\b", re.I)


def ear_checks(sents):
    """Whole sentences, not snippets: the read-aloud pass judges each one at pace."""
    ear = {}
    ear["trailing which-clauses (the point arrives in a subordinate clause)"] = [
        s for s in sents if re.search(r",\s+which\s+(?:is|was|are|were|isn't|wasn't|means)\b", s)]
    appended = []
    for s in sents:
        if "," not in s:
            continue
        head, _, tail = s.rpartition(",")
        # ", and you ..." is ordinary speech; the cheap-band signature is a subordinating clause
        if re.match(r"\s*(?:which|so that|because)\b", tail) and YOU.search(tail) and not YOU.search(head):
            appended.append(s)
    ear["you-clauses appended to a third-person sentence (how the band gets hit cheaply)"] = appended
    ear["referents held across a sentence (that much / half that / the one in)"] = [s for s in sents if REFERENT.search(s)]
    numfrag, cur = [], 0
    for i, s in enumerate(sents):
        cur = cur + 1 if (len(s.split()) <= 6 and NUMWORD.search(s)) else 0
        if cur == 3:
            numfrag.append(" / ".join(sents[i - 2:i + 1]))
    ear["number-fragment runs (3+ short sentences each carrying a number)"] = numfrag
    ear["abstract density (2+ abstraction words in one sentence)"] = [s for s in sents if len(ABSTRACT.findall(s)) >= 2]
    # a term whose definition arrives before its consequence: "…a printed pass with the seal on it, called a dastak"
    named_late = []
    for s in sents:
        m = re.search(r"(?<![A-Za-z])called (?:a|an|the) [a-z]", s)
        if m and m.start() > len(s) * 0.45:
            named_late.append(s)
    ear["term named after its definition (the viewer holds an unnamed thing meanwhile)"] = named_late
    # motif fatigue: the same long phrase returning verbatim, level callouts excluded
    words, seen, repeats = [], {}, []
    for s in sents:
        if re.match(r"\s*Level \w+[.,]", s):
            continue
        words += re.findall(r"[a-z']+", s.lower())
    for i in range(len(words) - 5):
        g = " ".join(words[i:i + 6])
        seen[g] = seen.get(g, 0) + 1
    repeats = [f"{g!r} x{n}" for g, n in seen.items() if n > 1]
    ear["phrases returning verbatim (a motif should change its angle, not its wording)"] = sorted(repeats)
    return ear


def band(n):
    return "S" if n <= 12 else ("M" if n <= 22 else "L")


def narration(path):
    lines = open(path, encoding="utf-8").read().split("\n")
    cut = next((i for i, l in enumerate(lines) if re.match(r"^#+\s*hand-?off", l.strip(), re.I)), len(lines))
    keep = [re.sub(r"\*\*|__|<!--.*?-->", "", l.strip()) for l in lines[:cut]
            if l.strip() and not l.strip().startswith(("#", "|", "-", ">", "<!--", "```", "!"))]
    return " ".join(keep)


def ctx(text, m, pad=45):
    return text[max(0, m.start() - pad):m.end() + pad].strip()


def main():
    args = sys.argv[1:]
    english = "british"
    if "--english" in args:
        i = args.index("--english"); english = args[i + 1].lower(); del args[i:i + 2]
    if not args:
        sys.exit(__doc__)
    text = narration(args[0])
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    lens = [len(s.split()) for s in sents]
    low = text.lower()
    findings = {}

    findings["em dashes"] = [ctx(text, m, 30) for m in re.finditer(EM, text)]
    # digits in narration are spoken as noise by the TTS; a heading's own number is fine
    findings["digits (write numbers as words)"] = [ctx(text, m, 30) for m in re.finditer(r"(?<![\w.])\d[\d,.]*", text)
                                                   if not re.match(r"^Level \d+\.$", ctx(text, m, 0))]
    findings["reveal-flips"] = [ctx(text, m) for m in FLIP.finditer(text)]
    findings["question-then-answer fragments"] = [ctx(text, m) for m in QA.finditer(text)]
    findings["summary tags"] = [ctx(text, m) for m in SUMTAG.finditer(text)]
    findings["characterised quotes"] = [ctx(text, m) for m in CHARQUOTE.finditer(text)]
    findings["announced moves"] = [ctx(text, m) for p in MOVES for m in re.finditer(re.escape(p), low)]
    findings["filler words"] = [ctx(text, m) for w in WORDS for m in re.finditer(r"\b" + w + r"\w*", low)]
    findings["filler phrases"] = [ctx(text, m) for p in PHRASES for m in re.finditer(re.escape(p), low)]
    findings["hedges / intensifiers"] = [ctx(text, m) for h in HEDGES for m in re.finditer(r"\b" + re.escape(h), low)]
    stacks, cur = [], 0
    for i, n in enumerate(lens):
        cur = cur + 1 if n <= 3 else 0
        if cur == 3: stacks.append(" ".join(sents[i - 2:i + 1]))
    findings["fragment runs (3+ of <=3 words; lists are fine)"] = stacks
    firsts = [re.sub(r"[^A-Za-z']", "", s.split()[0]).lower() for s in sents]
    ana, cur = [], 1
    for i, (a, b) in enumerate(zip(firsts, firsts[1:])):
        cur = cur + 1 if a == b else 1
        if cur == 3 and a != "you": ana.append(" / ".join(sents[i - 1:i + 2]))
    findings["anaphora runs (not 'You')"] = ana
    if english == "british":
        findings["american spellings / words"] = [ctx(text, m, 25) for m in re.finditer(AMERICAN, text, re.I)]

    # register bands measured from the POVrank corpus (research/artifacts/povrank-register-targets.md)
    wc = len(text.split())
    contractions = len(re.findall(r"\b\w+'(?:s|t|re|ve|ll|d|m)\b", text))
    you = len(re.findall(r"\b(?:you|your|you're|you've|you'll)\b", text, re.I))
    feeling = re.compile(r"\b(he|she|they|his|her|their|nobody|somebody|dies?|died|death|fear|afraid|"
                         r"hungry|cold|sick|debt|owe|pay|paid|buy|bought|lose|lost|wait|hope|shame|grief|kill|"
                         r"beat|carry|hold|walk|sign|stand|sit|watch|feel|felt)\b", re.I)
    fact_only = [s for s in sents if re.search(r"\d|hundred|thousand|million|per cent", s, re.I) and not feeling.search(s)]
    bands = [("mean sentence length", statistics.mean(lens), 8, 11, "words"),
             ("contractions per 100 words", 100 * contractions / max(1, wc), 0.2, 99, "per 100"),
             ("second-person density", 100 * you / max(1, wc), 5, 8, "per 100"),
             ("fact-only sentences", 100 * len(fact_only) / max(1, len(sents)), 0, 20, "%")]

    runs, cur = 0, 1
    for a, b in zip(map(band, lens), map(band, lens[1:])):
        cur = cur + 1 if a == b else 1
        if cur == 3: runs += 1
    q = sum(s.endswith("?") for s in sents)
    print(f"{args[0]}\nnarration: {len(text.split())} words, {len(sents)} sentences, mean {statistics.mean(lens):.1f} words "
          f"(sd {statistics.pstdev(lens):.1f}), same-length runs of 3+: {runs}, questions: {q}\n")
    for k, v in findings.items():
        print(f"{len(v):>3}  {k}")
    print()
    print("register bands (POVrank corpus; the fact-only figure uses this script's own stake-word list, so it reads lower than the study's):")
    for name, got, lo, hi, unit in bands:
        mark = "ok " if lo <= got <= hi else "OFF"
        print(f"  {mark} {name}: {got:.1f} {unit} (band {lo}-{hi})" if hi < 99
              else f"  {mark} {name}: {got:.1f} {unit} (at least {lo})")
    if fact_only:
        print(f"  fact-only sentences ({len(fact_only)}), the first few:")
        for s in fact_only[:5]:
            print("     " + s[:120])
    print()
    ear = ear_checks(sents)
    print("ear checks (pass every band, fail when spoken; the read-aloud pass judges each at pace):")
    for k, v in ear.items():
        print(f"{len(v):>3}  {k}")
    print()
    for k, v in list(findings.items()) + list(ear.items()):
        if v:
            print(f"## {k}")
            for x in v: print("   " + x[:160])
    return 1 if findings["em dashes"] else 0


if __name__ == "__main__":
    sys.exit(main())
