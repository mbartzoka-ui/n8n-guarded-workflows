# n8n workflows that stop before the irreversible part

Four n8n workflows for developer education and community work. They all do the
same five things in the same order:

```
fetch  →  reason with Claude  →  verify in code  →  human gate  →  publish (off)
```

The third step is the one that matters. **The model writes; plain JavaScript
checks its work.** A prompt asking a model not to invent things is a request. A
`Code` node that drops any claim it cannot find in the source is a gate. Every
workflow here has one, and each one is a different shape of the same idea:

| Workflow | What the model produces | What the code refuses to accept |
|---|---|---|
| [`forum-triage`](forum-triage.json) | a draft reply to an unanswered question | output it cannot parse — treated as low confidence, never as a confident draft |
| [`docs-gap-radar`](docs-gap-radar.json) | themes across a week of questions | a theme whose quoted evidence titles were not in the input |
| [`quiz-from-docs`](quiz-from-docs.json) | multiple-choice questions with an answer key | a question whose justification is not a verbatim sentence from the page |
| [`release-to-shortform`](release-to-shortform.json) | a 45-second script and social posts | a claim whose terms do not appear in the release note |

And the last node of every one is the same:

```
Publish (disabled on purpose)
```

It is present, wired, and switched off. Publishing is a decision, not a default.

---

## The four, briefly

### `forum-triage` — help the person who has been waiting longest

Reads a Discourse forum, keeps threads with no reply, and sorts **oldest first**.
The obvious sort is newest-first and it is wrong: someone who posted two days ago
and got silence needs help more than someone who posted ten minutes ago and is
still reading the docs. Sorting by age turns the queue into a queue of *people
waiting*, which is what it actually is.

### `docs-gap-radar` — a content backlog you did not have to guess at

Unanswered questions are the cheapest signal a community gives you. They tell you
what the documentation does not cover, in the words the person actually used. This
groups a week of them into themes, and throws away any theme the model cannot back
with at least two titles that really appeared in the input.

Requiring two is deliberate. One question is an anecdote.

### `quiz-from-docs` — assessment that has to cite its source

Every generated question must carry a `justification`: a sentence copied verbatim
from the page. The next node normalises whitespace and checks that the sentence is
genuinely in the page, and deletes the question if it is not.

An assessment built on a hallucinated justification teaches the wrong thing to
everyone who takes it — and does so with a confident answer key. That is worse
than having no quiz.

### `release-to-shortform` — copy that cannot outrun the changelog

Turns a release note into a short script and three channel variants. The model
must list every factual claim it made; the next node checks each one against the
release body and routes the whole draft back if any claim is unsupported.

Marketing copy that invents a feature is the expensive kind of wrong: it reaches
more people than the correction ever will.

---

## Checking them

```bash
python validate.py
```

```
ok    docs-gap-radar.json  (10 nodes)
ok    forum-triage.json  (10 nodes)
ok    quiz-from-docs.json  (10 nodes)
ok    release-to-shortform.json  (10 nodes)

4/4 workflows passed
```

No dependencies. It checks structure — required fields, unique names, connections
pointing at nodes that exist, no unreachable nodes — plus embedded JavaScript
syntax when `node` is on your PATH, and it refuses anything that looks like a
committed credential or a real email address.

The check worth having is **unconnected outputs**:

```
'Any gaps worth writing?' output #1 is declared but connected to nothing
    — items routed there vanish silently
```

A router with a branch that goes nowhere quietly discards whatever lands in it.
Nothing is labelled, nobody is notified, no draft appears. It reads as a quiet day
rather than a bug. I found exactly that in a workflow of my own — a five-way
classifier whose "unclassified" branch was connected to nothing — which is why it
is the first thing this script looks for.

---

## Running any of them

Import the `.json` into n8n: paste it onto the canvas, or **Import from File**.
Then:

1. Attach an **Anthropic** credential to the `Claude` node.
2. The review gates use a **Wait** node with form resume, so they need no
   credentials at all. n8n gives you a URL; opening it and submitting continues
   the run.
3. Point the HTTP Request node at your own source. Defaults are public endpoints
   that need no key: `community.n8n.io/c/<slug>/<id>.json` for any Discourse
   category, `api.github.com/repos/<org>/<repo>/releases` for release notes.

## Honest status

These are working designs, not battle-tested production systems. The JSON is
valid, the graphs are complete, the embedded JavaScript parses, and the safety
decisions are already made — but none of them has run unattended for weeks, and
the forum category ids and docs URLs are specific to one product.

Treat them as starting points that already have the awkward decisions made.

If you find a case where one of the verification steps lets something through
that it should have caught, that is the interesting bug — open an issue.

---

Built by [Maria Bartzoka](https://www.linkedin.com/in/mariabartzoka) ·
[thetaai.gr](https://thetaai.gr) ·
[TEDx: Where Fashion Meets AI](https://www.youtube.com/watch?v=16iD6aorhEg)

MIT licensed — see [LICENSE](LICENSE).
