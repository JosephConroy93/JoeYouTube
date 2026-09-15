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
    for k, v in findings.items():
        if v:
            print(f"## {k}")
            for x in v: print("   " + x[:160])
    return 1 if findings["em dashes"] else 0


if __name__ == "__main__":
    sys.exit(main())
