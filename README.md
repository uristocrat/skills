# Skills and Agents Library

**Skills that make [Claude Code](https://claude.ai/code) more capable. Install one with a single command.**

Browse the live catalog at **[skillsandagents.co](https://skillsandagents.co)** · Built and maintained by [Skills and Agents Co](https://skillsandagents.co)

---

Each skill adds a specific capability to Claude: check your business cashflow, see where your brand shows up in ChatGPT, fix your Ghost site's Google indexing, walk through filing an unemployment claim. One install, and Claude instantly knows how to do the job.

This repo is the source of truth for every skill we publish. Each is MIT-licensed, version-tagged, and ready to drop into Claude Code, Claude Desktop, or any Anthropic-compatible runtime that loads `SKILL.md` files.

## Install the plugin marketplace

Add the marketplace once, then install any plugin from it:

```bash
/plugin marketplace add skills-agents-co/skills-and-agents-library
```

```bash
/plugin install financial-pulse@skills-and-agents
```

Swap `financial-pulse` for any plugin listed in [`.claude-plugin/marketplace.json`](./.claude-plugin/marketplace.json). `financial-pulse` connects to Mercury, Ramp, and Grasshopper for a cashflow pulse. `product-builder` bundles code review, PR summaries, research briefs, competitor intel, and document drafting.

## Who this is for

- **End users** who want Claude to handle a specific task end-to-end — no prompting tricks, no glue code. Pick a skill, install it, ask Claude.
- **Product managers** evaluating what Claude skills look like in the wild — real-world scope, packaging, and triggers worth borrowing.
- **Developers** building their own skills and agents — every folder here is a working reference you can fork, study, or PR against.

## What's inside

### Find a skill by what you want to do

| I want to… | Use | Type |
| --- | --- | --- |
| **Fix my Ghost blog's Google indexing** automatically (Search Console → diagnose → fix → resubmit) | [`ghost-seo-agent/`](./ghost-seo-agent) | agent |
| **See where my brand shows up in ChatGPT, Perplexity, and Claude** — and what to write to close the gap | [`llm-visibility-agent/`](./llm-visibility-agent) | agent |
| **Get a weekly cashflow pulse** across Mercury, Ramp, and Grasshopper | [`financial-pulse/`](./financial-pulse) | skill + 3 agents |
| **Run buy-side due diligence on a private company** before you buy it (QoE, red-flag matrix, valuation impact) | [`buy-side-diligence/`](./buy-side-diligence) | skill |
| **Chat with my ad and analytics data and get ranked optimization moves** across Google Ads, Meta, TikTok, LinkedIn, GA4, and Stripe | [`ads-copilot/`](./ads-copilot) | skill |
| **Strip the AI tells from my Office docs** before they ship — pipe separators, em dashes, default colors, Sheet1 names, and other machine-generated giveaways in .pptx/.docx/.xlsx | [`office-tells/`](./office-tells) | skill |
| **Actually understand the code Claude just wrote** — a teaching loop that quizzes you on the problem, solution, design decisions, and edge cases until you've demonstrably got it | [`learn-quiz/`](./learn-quiz) | skill |
| **Turn a meeting transcript into structured meeting memory** — a dated meeting note, one mention line per person/company you track, and a recap email drafted (never sent) | [`meeting-scribe/`](./meeting-scribe) | skill |
| **Prep for an upcoming meeting** — read your calendar export, match attendees and companies against the people/companies you track, and get a dated brief with their full mention history before you walk in | [`calendar-agent/`](./calendar-agent) | skill |
| **Get a news pulse on the people and companies you track** — filtered against your own tracked entities, not a generic feed, with a dated digest naming what was found or plainly saying nothing was | [`news-monitor/`](./news-monitor) | skill |
| **Turn your meeting notes into content ideas** — find the ideas that keep recurring across more than one meeting and draft a short, quote-grounded post for each one | [`librarian/`](./librarian) | skill |

More skills land here regularly. **[Star or watch this repo](https://github.com/skills-agents-co/skills-and-agents-library)** or follow the [catalog](https://skillsandagents.co) to catch new releases.

## Install in 30 seconds

Every skill installs the same way: download one pinned tarball, extract the skill's whole folder into `~/.claude/skills/`, then restart Claude Code. Extracting the folder, not just `SKILL.md`, is what brings along the `scripts/` and `references/` files a skill's own instructions actually run.

```bash
(
  set -e
  skill="resume-tailor"   # <-- change me to the skill's folder (see note below)
  ref="v1.31.0"            # pinned release; matches index.json's skillFileUrl

  # The install removes "$HOME/.claude/skills/$skill" before it copies. If
  # $skill were empty or a path, that line would delete the wrong directory —
  # every skill you have installed — so refuse anything but a plain name.
  # The last arm rejects any character outside a folder name, which also keeps
  # a glob like "*" out: bsdtar treats a member pattern as a glob, so "*" would
  # extract the entire repository instead of one skill.
  case "$skill" in
    ""|.|..|*/*|-*|*[!A-Za-z0-9._-]*)
      echo "Set skill to a plain folder name, e.g. resume-tailor" >&2; exit 1 ;;
  esac

  work="$(mktemp -d)"
  trap 'rm -rf "$work"' EXIT

  curl -fsSL --connect-timeout 10 --max-time 120 --retry 3 --retry-delay 2 \
    --retry-connrefused --retry-max-time 120 -o "$work/repo.tgz" \
    "https://codeload.github.com/skills-agents-co/skills-and-agents-library/tar.gz/$ref"

  mkdir -p "$work/staged"
  topdir="$(tar -tzf "$work/repo.tgz" | grep -m1 '/' | cut -d/ -f1)"
  tar -xzf "$work/repo.tgz" --strip-components=2 --no-same-owner --no-same-permissions \
    -C "$work/staged" "$topdir/$skill"

  dest="$HOME/.claude/skills/$skill"
  rm -rf "$dest"
  mkdir -p "$(dirname "$dest")"
  cp -R "$work/staged" "$dest"

  echo "Installed to $dest"
)
```

The block runs in a subshell (the parens) so `skill`, `ref`, and the other variables it sets do not leak into your shell, and `set -e` inside it means a failed download or a bad skill name stops the install instead of leaving a half-populated directory that looks successful. It downloads and unpacks into a scratch directory first and only touches `~/.claude/skills/` once the extraction has succeeded, so a failed install leaves nothing behind: no empty skill folder for Claude Code to find, and no stray tarball. Re-running it replaces the install rather than merging into it, so a file dropped from a later release does not survive as a stale leftover.

**What to put in `skill`.** For almost every entry it is the folder name shown in the table above (`resume-tailor`, `ceo-todo`, and so on) — which is also the slug. It is **not** the slug for the four agents that ship inside another skill's folder: `ceo-todo-daily` installs as `skill="ceo-todo"`, and `financial-pulse-grasshopper`, `financial-pulse-mercury`, and `financial-pulse-ramp` all install as `skill="financial-pulse"`. Installing one of those pulls in the whole parent skill (including its other agents), which is expected — the agent file itself is the payload you actually run.

**Installing an agent takes one more step.** Claude Code loads subagents from `~/.claude/agents/`, not from inside a skill folder, so the four agent entries above need their markdown copied out after the install block runs. Otherwise the file is on disk and the agent still does not register:

```bash
(
  set -e
  agent="ceo-todo-daily"   # <-- or financial-pulse-grasshopper / -mercury / -ramp
  skill="ceo-todo"         # <-- the folder it ships in, per the paragraph above

  # Each name is checked on its own. Testing "$agent$skill" would only catch an
  # empty value when BOTH were empty, so an empty $agent with a real $skill
  # sailed through.
  for name in "$agent" "$skill"; do
    case "$name" in
      ""|.|..|*/*|-*|*[!A-Za-z0-9._-]*)
        echo "Set agent and skill to plain names, e.g. ceo-todo-daily / ceo-todo" >&2; exit 1 ;;
    esac
  done

  mkdir -p "$HOME/.claude/agents"
  cp "$HOME/.claude/skills/$skill/agents/$agent.md" "$HOME/.claude/agents/$agent.md"
  echo "Installed agent to $HOME/.claude/agents/$agent.md"
)
```

The fastest path is **[skillsandagents.co](https://skillsandagents.co)** — every skill's catalog page will generate this exact pinned command for you, copy-paste ready, once the catalog site adopts the manifest this repo now publishes. Until then it still generates the older single-file command, so the command above is the one to use by hand in the meantime.

> Two skills nest their `SKILL.md` one level deeper: `ads-copilot` and `financial-pulse`. The command above still extracts their whole folder correctly, but `SKILL.md` lands at `$dest/skills/<skill-name>/SKILL.md` instead of at the top, where Claude Code looks for it. Run this once more, right after the block above, for those two:
>
> ```bash
> (
>   set -e
>   skill="ads-copilot"   # or "financial-pulse"
>   mv "$HOME/.claude/skills/$skill/skills/$skill/SKILL.md" "$HOME/.claude/skills/$skill/SKILL.md"
> )
> ```
>
> `references/` and `scripts/` are already siblings of the moved `SKILL.md`, which is where its own text expects them. Every other skill in this repo is flat and needs no extra step.

## Install via skills.sh

These skills are also installable through [skills.sh](https://skills.sh), the open skills registry. Install the whole catalog at once:

```bash
npx skills add skills-agents-co/skills-and-agents-library
```

Or pull a single skill by its slug:

```bash
npx skills add skills-agents-co/skills-and-agents-library --skill <slug>
```

Available skills and their slugs:

- `learn-quiz` (make Claude teach you the work until you actually understand it)
- `ghost-seo-agent` (diagnose and fix Ghost Google indexing)
- `office-tells` (strip the AI tells from .pptx/.docx/.xlsx)
- `buy-side-diligence` (run buy-side due diligence on a private company)
- `llm-visibility-agent` (see where your brand shows up across ChatGPT, Perplexity, and Claude)
- `financial-pulse` (weekly cashflow pulse across Mercury, Ramp, and Grasshopper)
- `ads-copilot` (chat with your ad and analytics data for ranked optimization moves)
- `meeting-scribe` (turn a meeting transcript into structured meeting memory, inspired by USV)
- `calendar-agent` (prep briefs for upcoming meetings against your tracked people/companies, inspired by USV)
- `news-monitor` (news digests on your tracked people/companies filtered against your own entity files, inspired by USV)
- `librarian` (recurring themes from your meeting notes drafted into short posts, inspired by USV)

The full catalog, with per-skill pages and pinned install commands, lives at [skillsandagents.co](https://skillsandagents.co/). Skills surface on skills.sh automatically through install telemetry, so there is no registration step on our end.

## Why these skills exist

Every skill in this repo solves a problem we actually had running our own companies — then we generalized it so anyone can use it.
We pin every install URL to a tagged release (never `main`), so the skill you install today behaves the same way next month.

## For skill authors

This repo doubles as a working reference for how we package skills:

- **`SKILL.md` with rich YAML frontmatter** — name, description, and trigger phrases that Claude actually matches against
- **One folder per skill**, supporting files in `references/`, `agents/`, `scripts/`
- **Tagged releases** — `v1.0.0`, `v1.1.0`, etc. — with a generated [`index.json`](./index.json) the catalog consumes
- **Contribution path** in [CONTRIBUTING.md](./CONTRIBUTING.md): new skill = new top-level folder, one PR

Cutting a release:

The index is committed **before** the tag is placed, not after. Tagging first would leave the tag's own tarball carrying the *previous* release's `index.json`, so the manifest a user downloads would never describe the download it came in.

> **A release commit does not go through a pull request.** It is the one commit in this repo that pushes straight to `main`, with the tag created and pushed in the same motion. The reason is mechanical, not stylistic: a release commit bumps `index.json` and the `ref="…"` line above to a tag **that does not exist yet**, and `scripts/check-index-additive.mjs` and `scripts/test-install.sh` both resolve that ref. Opened as a PR, the release commit is red by construction, and there is no green state to merge — the ref only becomes resolvable once the tag is pushed, which happens after the merge. So: land the content changes through PRs as usual, then cut the release as a direct push. Nothing else in this repo is allowed to bypass review this way.

1. Bump `version` in frontmatter for any changed `SKILL.md`. This is normal PR work, reviewed like anything else, and it lands before the release commit.
2. On an up-to-date `main`, rebuild the index for the tag you are about to cut: `node scripts/build-index.mjs --tag v1.x.0 --worktree`. `--worktree` is required here and only here — the tag does not exist yet, so there is no ref to read content from, and the working tree is what is about to become that tag.
3. **In the same commit**, bump the `ref="v1.x.0"` line in the install block above to the new tag. `scripts/check-index-additive.mjs` fails the build if the README's ref and `index.json`'s ref disagree, so this is not optional and CI will say so.
4. Commit the regenerated `index.json` and the README together, directly on `main`.
5. Tag that commit and push both **in one command**: `git tag v1.x.0 && git push --atomic origin main v1.x.0`. `--atomic` is what makes this one command: either the commit and the tag both land or neither does. Without it, a partial push leaves `main` briefly pinned to a ref nobody can resolve, which is exactly the red state this step exists to avoid.
6. Only now do the ref-resolving local checks mean anything. Run `node scripts/check-index-additive.mjs`, `bash scripts/test-install.sh`, and `bash scripts/test-readme-install.sh` against the pushed tag. Running them between steps 2 and 5 is expected to fail and tells you nothing.

Because the tag lands on the commit that already holds the matching `index.json`, the tag-push build checks the tag against its own manifest rather than against the last release's, and re-running `node scripts/build-index.mjs --tag v1.x.0` afterwards reproduces the committed file byte for byte.

**On a normal pull request none of this bites.** A PR does not touch the pinned ref, so the ref `index.json` names is the last release's tag, which resolves fine, and every check runs for real. The only PR that would go red by construction is one that bumps the ref — and that is precisely the commit the note above says not to open as a PR.

`index.json` describes the tagged release, not your checkout: `build-index.mjs --tag v1.x.0` reads the repo's contents **at that tag**, and `scripts/test-install.sh` verifies the published `files` manifest against that same tag's tarball. That is why a pull request adding a file inside a skill folder does not need to regenerate `index.json` — the new file joins the manifest at the next release, and until then both checks are looking at the same snapshot. If the tag is not in your clone the build fails rather than quietly reading your working tree instead; run `git fetch --tags`, or pass `--worktree` when reading the working tree is what you actually want.

## License

MIT — see [LICENSE](./LICENSE). Individual skill folders may carry their own license file if imported from a separately-licensed source.

---

**Questions, bug reports, or skill ideas?** Open an [issue](https://github.com/skills-agents-co/skills-and-agents-library/issues) or PR. We read every one.
