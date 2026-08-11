# Community forum triage — an n8n workflow that drafts, but never posts

An n8n workflow that reads a Discourse community forum, finds questions nobody
has answered, drafts a reply with Claude, and then **stops and waits for a
human**.

The stopping is the point. Everything else is plumbing.

```
Every morning 08:00
  → Fetch Questions category          Discourse JSON, no API key needed
  → Keep unanswered, oldest first     reply_count === 0, sorted by age
  → Anything to answer?               exits cleanly when there is nothing
  → Draft a reply ── Claude
  → Parse + flag low confidence
  → One digest, not ten emails
  → HUMAN GATE                        approve before anything is posted
  → Post to forum                     DISABLED ON PURPOSE
```

## Three decisions worth explaining

Most of a workflow is obvious once you see it. These three are not, and they are
the reason this exists rather than a tutorial version.

### 1. Oldest first, not newest first

```js
.sort((a, b) => b.json.age_hours - a.json.age_hours)
```

The obvious sort is newest-first — it feels responsive. It is wrong. Someone who
posted two days ago and got silence needs help more than someone who posted ten
minutes ago and is still reading the docs. Sorting by age turns the queue into a
queue of *people waiting*, which is what it actually is.

### 2. The model is told to admit when it does not know

The prompt asks for a confidence level and says, in as many words:

> If you are not confident the answer is correct, say so explicitly and set
> confidence to "low". A wrong instruction costs more than no instruction.

And because an instruction is a request rather than a guarantee, unparseable
model output is treated as low confidence automatically:

```js
} catch {
  parsed = { confidence: 'low', needs_human: true, parse_failed: true, ... };
}
```

A garbled response must never become a confident-looking draft. The failure mode
worth designing against is not "the model says nothing" — it is "the model says
something wrong, fluently."

### 3. The node that would publish exists, and is switched off

```
Post to forum (disabled on purpose)
```

It is in the canvas, wired up, and disabled. That is deliberate. Publishing is a
decision, not a default. Nothing reaches that node without an explicit human
approval upstream, and turning it on should be something a person does once the
drafts have earned it — not something that was true from the first run.

The same principle shows up in the smaller choices: replies are drafted, not
sent; results arrive as one digest rather than ten separate emails; and a run
with nothing to do exits quietly instead of producing noise.

## Running it

Import `forum-triage.json` into n8n — paste it straight onto the canvas, or use
**Import from File**. Then:

1. Attach an **Anthropic** credential to the `Claude` node.
2. Attach a **Gmail** credential to the approval node, and change `sendTo` from
   the `you@example.com` placeholder to your own address. If Gmail OAuth is more
   setup than you want, a **Wait** node with form resume gives you the same gate
   with no credentials at all.
3. Point the HTTP Request node at your own forum. The URL in the workflow is
   `community.n8n.io/c/questions/9.json`; any Discourse instance exposes the same
   shape at `/c/<slug>/<id>.json`, and no API key is required for public
   categories.

## Honest status

This is a working design, not a battle-tested production system. The JSON is
valid and the node graph is complete and connected, but it has not run
unattended for weeks, and the Discourse category id is specific to one forum.
Treat it as a starting point that already has the safety decisions made, rather
than something to switch on and forget.

If you find a case where the confidence gate lets something bad through, that is
the interesting bug — open an issue.

## Why a triage workflow at all

Unanswered questions are the cheapest signal a community gives you. They tell
you what the documentation does not cover, in the words the person actually used.
A queue of them, sorted by how long someone has been waiting, is a
better content roadmap than most content roadmaps.

Drafting the answers is a convenience. Seeing the queue is the value.

---

Built by [Maria Bartzoka](https://www.linkedin.com/in/mariabartzoka) ·
[thetaai.gr](https://thetaai.gr) ·
[TEDx: Where Fashion Meets AI](https://www.youtube.com/watch?v=16iD6aorhEg)

MIT licensed — see [LICENSE](LICENSE).
