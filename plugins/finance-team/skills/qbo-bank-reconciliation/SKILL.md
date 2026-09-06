---
name: qbo-bank-reconciliation
description: >
  Matches bank transactions against the QuickBooks Online register and the
  petty cash log for a stated period, so cash gets reconciled first in the
  close instead of last. It pulls the bank side from a connected bank MCP
  (the financial-pulse connector pattern: Grasshopper, Mercury) or from an
  uploaded or pasted statement, and the QBO side through the QuickBooks
  Online MCP (intuit/quickbooks-online-mcp-server). It finds exact matches
  (same amount, same payee, date inside a stated tolerance window) and
  proposes them for the bookkeeper to approve in QBO. It lists everything
  that isn't an exact match separately: amount mismatches, missing
  counterparts, duplicate candidates. It writes nothing to QBO or to the
  bank. It's read-only by design. Use it whenever the user says "reconcile
  the bank", "run bank rec", "match the bank feed", "petty cash
  reconciliation", "close the books on cash", "what doesn't match in the
  bank register", "bank and petty cash close", "QBO bank reconciliation",
  or anything else that means they want to confirm cash cleared clean for
  the period. Always use this skill for QBO bank-and-petty-cash close work.
  Don't freehand a reconciliation without it.
license: MIT
---

# QBO Bank & Petty Cash Reconciliation

Confirm that cash is clean for the period. This matches the bank feed and
the petty cash log against the QuickBooks Online register, so bank rec
comes off the close checklist first instead of getting circled back to
again and again.

## Role

You are a cash reconciliation assistant for a bookkeeper. You pull the
bank side of the period from a connected bank MCP or an uploaded
statement. You pull the QBO register and the petty cash total for the same
period. You match the two sides.

You propose exact matches for the bookkeeper to approve in QBO. You never
approve anything. You never post anything. You never write anything to QBO
or to the bank. Put every non-exact item on a discrepancy list that a
human can act on. Never fold a non-exact item into a false "reconciled"
summary.

## Before you start: confirm read-only access

This skill calls the QuickBooks Online MCP server
(`intuit/quickbooks-online-mcp-server`) for reads only. Confirm that the
MCP starts with its write tools off:

```
QUICKBOOKS_DISABLE_WRITE=true
QUICKBOOKS_DISABLE_UPDATE=true
QUICKBOOKS_DISABLE_DELETE=true
```

That MCP server's own README documents these env var names as of this
skill's writing. MCP server flags change between releases. Confirm the
names against the version that you run. If you cannot confirm that the
write tools are off, tell the user to check before you proceed.

This skill never calls a `create_*`, `update_*`, or `delete_*` tool
itself. That rule holds whatever the MCP configuration says. The env vars
are a second guarantee. They do not replace this skill's own read-only
behavior.

The same rule covers the bank side. This skill reads transaction data only
from whichever bank MCP is connected. That covers Grasshopper, Mercury, or
another `financial-pulse` connector that exposes bank-transaction data. It
never calls a tool that starts a transfer, moves funds, or modifies the
account. That rule holds even when the connected MCP exposes such a tool.

## Step 1: Resolve the Bank Source and Account

Determine where the bank-side data comes from before you pull anything.
Follow the same bank-agnostic pattern that `financial-pulse` uses:

1. **A connected bank MCP** (preferred): Grasshopper, Mercury, or any
   other bank MCP already connected in the session that exposes a
   bank-transaction or statement feed. Use its read-only tools to pull the
   period's transactions.
2. **An uploaded or pasted statement**: a CSV export, or a pasted
   transaction list from the bookkeeper's bank. Use this when no connector
   is available.

**Ramp is a corporate-card and spend platform, not a bank. It exposes card
spend events and linked-account metadata. It does not expose a bank
statement or a bank-transaction loader — see the `financial-pulse` skill's
Ramp agent.** Never offer Ramp
here. A comparison of Ramp's card and spend records against a QBO bank
register compares two different things. It produces matches that do not
mean what they look like. A cash side that runs through Ramp needs a
different reconciliation than this skill performs. Say so, rather than
running this one anyway.

**Ask the bookkeeper which specific bank account this run reconciles if
the connected source exposes more than one account.** Grasshopper's
connector, for example, fetches transactions across every linked account.
Ask which QBO bank-account ledger that bank account maps to. Scope every
pull below to that one account pairing.

Never mix checking, savings, or treasury activity from multiple accounts
into one reconciliation. A transaction from the wrong account can produce
a match that is really a coincidence. It can also produce a false
missing-counterpart for an account that this run never covered. A
bookkeeper with several accounts to reconcile runs this skill several
times, one account pairing per run.

Stop and ask before you proceed if you have no bank source or no account
pairing:

"I need bank-side data to reconcile against QBO. You can:
- Connect a bank that supports MCP (Grasshopper, Mercury, or another
  supported bank, not Ramp, which doesn't expose bank statement data)
- Upload a CSV export from your bank
- Paste your recent bank transactions

I also need to know which QBO bank account this reconciles against, if
your bank connection covers more than one account."

Never report a "reconciled" state without bank data and a resolved account
pairing. That rule covers a partial state too. A close step that silently
skips the bank pull and calls itself done is worse than no automation at
all. A close step that silently mixes accounts is worse in the same way.

## Step 2: Establish the Period

Ask the user for the reporting period if the user did not state it. An
example period is "May 2026" or "last calendar month". Anchor the
bank-side pull and the QBO-side pull to the start date and the end date of
this period. Resolve a relative period against today's date. State the
resolved range back to the user before you continue.

Stop if the resolved period is longer than about a year. Confirm the
period with the user before you pull anything. This skill covers one month
or one quarter at a time. A multi-year pull risks an unbounded number of
transactions from the bank source and from the QBO MCP. It is also
probably not what the user wants to reconcile in one pass.

## Step 3: Setup Disclaimer & Tolerance (first run for this client)

State the disclaimer below to the bookkeeper before you show any proposed
match. Do this on the first run for a client. Do it also whenever no
tolerance is set for this client in this session:

> **Heads up:** "Exact match" here means the same amount, the same payee,
> and a date inside the tolerance window below. It doesn't guarantee a
> match. A proposed match can still be wrong: say, two same-day,
> same-amount transactions to the same payee. Review every proposed match
> before you approve it in QBO. This skill never writes anything for you.

The default tolerance window is **±2 business days**. Bank processing lag
from ACH and check clearing is the norm, not the exception. A same-day,
same-amount, same-payee match is the highest-confidence tier inside that
window.

> **Tips on adjusting the tolerance:**
> - A business with frequent same-day duplicate transactions, like
>   recurring vendor charges, gets more false matches from a wider date
>   window. Tighten it toward same-day-only.
> - If your bank source lags QBO by more than the default window (ACH
>   clearing delays, say), widen the window. Don't accept a
>   non-exact-match pile that grows every month.
> - You can state a different tolerance in plain language at the start of a
>   run, like "use a 3-day window this time". This skill uses it for that
>   run. You don't need to edit the skill file.
> - Not sure? Start with the default. Tighten or widen it after the first
>   month's discrepancy list shows whether it over-matches or
>   under-matches.

Use the tolerance that the bookkeeper states for the run, and note the
override in the output. Use the ±2 business-day default otherwise.

## Step 4: Pull the Bank Side

**This skill makes a small, fixed number of calls per run. It makes one
bank-side pull here. It makes three QBO pulls in Step 5: the register, the
bank account balance, and petty cash. That is four calls for a normal
run.** The count does not change with the number of transactions on either
side.

Nothing in this skill loops per transaction. Nothing in this skill
re-pulls a report. A connected source may paginate internally for a
high-volume account. Follow its pagination in that case, rather than
assuming a single page. That pagination is the source's own concern. It is
not a reason for this skill to make more top-level calls.

Use the source and the account that you resolved in Step 1. Pull every
transaction dated inside the period. Also pull a buffer on each end equal
to the tolerance window, **for matching only**. A transaction can clear just outside
the period boundary. The buffer keeps that transaction available as a
match candidate for a nearby in-period QBO line.

**The buffer is not part of the period.** Take a bank-side transaction
whose own date falls inside the buffer and outside the stated period. That
transaction is not a bank-only discrepancy when it finds no QBO
counterpart. It is out of scope for this run. Exclude every unmatched
buffer-only transaction before Step 6 reports anything as bank-only or
missing. A buffer-only transaction is one dated in the buffer and not in
the stated period. Only a transaction dated inside the stated period is
eligible for a discrepancy report.

**Apply the connector's own status or completion filter before matching,
if its instructions define one.** For example, `financial-pulse-mercury.md`
requires a filter on `listTransactions` to the completed `sent` status. A
pending, failed, reversed, cancelled, or blocked Mercury transaction never
posts to QBO. Without the filter it becomes a false bank-only discrepancy,
or a spurious proposed match. Apply the equivalent completed or posted
filter for whichever connector you use, per its own documented statuses.

Capture these fields for each transaction. Capture the date, the amount,
and the payee or description. Capture a stable transaction ID or reference
if the source provides one. Capture whether the amount is signed as a
debit or withdrawal, or as a credit or deposit. Step 6 explains why the
sign matters before matching.

**Stop here if this pull errors, times out, or returns malformed data.
Stop here also if it comes back unexpectedly empty or incomplete for a
period where the user expects activity. Do not continue to Step 5 or Step
6.** Tell the user that the bank-side pull failed. Tell the user why. A
match against a broken or partial bank-side pull labels every QBO line as
missing its counterpart. It can also omit real bank-only discrepancies.
Both give a false-complete result that looks like a real reconciliation
and is not. This skill exists to prevent that failure.

## Step 5: Pull the QBO Side

Pull these for the same period with the QuickBooks Online MCP:

- **Bank register**: the QBO-side transactions posted to the bank account
  that you reconcile
- **Bank account balance**: the ending balance of the QBO bank account as
  of the period end date
- **Petty cash total**: the petty cash account balance and activity for
  the period, from the QBO ledger

Also get the **bank statement's ending balance** for the same period end
date. Ask the bookkeeper for it. Read it from the bank-side source instead
if that source states one.

**Transaction-level matching alone does not prove that cash is
reconciled.** It proves only that the transactions on both sides agree
with each other. An opening-balance discrepancy can leave every available
transaction matching cleanly while the bank and the books still disagree
in total. So can a transaction omitted from both sides. So can an old
outstanding check.

So do one more comparison, in addition to the Step 6 transaction match.
Compare the bank statement's ending balance against the QBO bank
account's ending balance:

- Say so explicitly if the two balances agree. Agreement is real evidence
  for "reconciled". It is more than an absence of transaction-level
  discrepancies.
- Outstanding items must explain the gap if the two balances disagree.
  Those items sit in the Step 9 discrepancy list. An outstanding item is a
  transaction recorded in QBO and not yet cleared at the bank, or the
  reverse. State the balance gap explicitly. State whether the sum of Step
  9's open items accounts for the gap. Say so plainly if it does not.
  Never describe cash as reconciled in that case. An unexplained balance
  gap is real evidence that something is still missing. That holds even
  when no single transaction-level mismatch points to it.

Capture the date, the amount, the payee, and the account for each register
line.

**Stop here if any of the three pulls fails. That covers the register
pull, the account-balance pull, and the petty cash pull. A failure is an
error, a timeout, or malformed data. Stop here also if
one of them comes back empty for a period where the user expects
activity.** Tell the user which pull failed and why. Do not continue into
Step 6 with partial data.

## Step 6: Match Bank Side Against QBO Side

**Normalize how each side signs a withdrawal and a deposit, before you
compare amounts.** An uploaded statement can encode a withdrawal as a
negative number. It can also split debits and credits into separate
columns. QBO's register may use a different convention. A direct
comparison of the raw captured amounts can classify every withdrawal as an
amount mismatch. That happens even when the two transactions are
identical.
`financial-pulse`'s own pattern normalizes this first. Do the same here.
Resolve both sides to one consistent signed representation, or to one
consistent debit and credit label. Do that before you apply the
amount-equality check below.

Look for a QBO register line for every bank-side transaction. The register
line must meet all three of these:

- **Amount** matches exactly, on the normalized direction-consistent
  values from above
- **Payee** matches. Allow reasonable normalization, such as "AMEX
  EPAYMENT" against "American Express". Never guess across genuinely
  different payees.
- **Date** falls inside the resolved tolerance window of the bank-side
  date

Classify each bank-side transaction:

- **Exact match**: one QBO register line satisfies all three criteria,
  and no other register line is an equally good candidate
- **Non-exact match**: an amount mismatch, a date outside the window, a
  payee mismatch, or ambiguity between two or more candidates
- **Missing counterpart**: you found no QBO register line at all

Do the same in reverse for a QBO register line with no bank-side
counterpart. Those lines are also missing counterparts, from the other
direction.

Flag any transaction that matches more than one candidate on the other
side. Call it a **duplicate candidate**. Never pick one candidate
silently.

## Step 7: Reconcile Petty Cash

**A petty cash disbursement is cash paid out of the physical fund. It
never touches the bank. So the Step 4 bank-side pull cannot verify it.**
Consider a bookkeeper who followed only the connector path or the
statement path in Step 1. That bookkeeper never separately supplied a
petty-cash log or a physical count. This skill then cannot confirm that petty cash is
right. It sees only bank withdrawals and QBO's recorded activity. Neither
one sees the cash once it leaves the fund.

Ask the bookkeeper directly for the fund's ending physical count, or for a
petty-cash log that covers the period. Get one of the two before you treat
this step as verified. **Never describe petty cash as reconciled if the
bookkeeper provides neither. Mark it in the output as "petty cash:
unreconciled, no physical count or log provided" instead.** Never let its
absence read as "nothing to report".

Compare the Step 5 petty cash total against the count or log, when the
bookkeeper provides one. Compare it also against any petty cash entries in
the bank-side data. Cash withdrawals for the petty cash fund and
replenishment transactions are examples of those entries.

Petty cash activity with no bank-side counterpart at all is expected. A
cash disbursement paid out of the fund itself is one example. Such
activity is not a discrepancy on its own. Flag it, though, when the fund's QBO
balance does not tie to the stated physical count. Flag it also when the
balance does not tie to the replenishment amount.

## Step 8: Report the Proposed Matches

```
## Proposed Exact Matches for [period]

| Date (bank) | Date (QBO) | Amount | Payee (bank, raw) | Payee (QBO, raw) | Confidence |
|-------------|------------|--------|--------------------|-------------------|------------|
| …           | …          | $…     | …                  | …                 | Highest / Within window |

These are proposals, nothing more. Review and approve each one in QBO
yourself. This skill hasn't written anything to QBO or to your bank.
```

**Show the raw payee text from each side separately. Never collapse the
two into one normalized value.** The payee match in Step 6 allows
reasonable normalization, such as "AMEX EPAYMENT" against "American
Express". One blended Payee column would hide that normalization from the
bookkeeper. The Step 3 disclaimer explicitly asks the bookkeeper to review
every proposed match before approving it. A bookkeeper cannot validate a
normalized match without seeing both original values behind it.

## Step 9: Report Non-Exact Matches and Discrepancies

Never fold a non-exact item into the "reconciled" summary. List every one
of them separately:

```
## Non-Exact Matches / Discrepancies for [period]

| Type | Bank Date | QBO Date | Amount | Payee | Issue |
|------|-----------|----------|--------|-------|-------|
| Amount mismatch | … | … | $… vs $… | … | … |
| Missing counterpart (bank-only) | … | n/a | $… | … | No matching QBO register line |
| Missing counterpart (QBO-only) | n/a | … | $… | … | No matching bank transaction |
| Duplicate candidate | … | … | $… | … | Matches more than one line on the other side |

None of these count toward the proposed matches above until someone sorts
them out.
```

Say so plainly if there is nothing to flag. Never omit the section.

## Output Sequence

1. The resolved bank source, as a connector or an uploaded or pasted file,
   and the resolved period
2. The setup disclaimer and the tolerance from Step 3, including any
   per-run override
3. The proposed exact matches from Step 8
4. The non-exact matches and discrepancies from Step 9
5. The petty cash reconciliation summary from Step 7

## What this skill never does

- It never calls a `create_*`, `update_*`, or `delete_*` tool on the
  QuickBooks Online MCP.
- It never calls a tool on a bank MCP that starts a transfer, moves funds,
  or modifies the account.
- It never approves, posts, or clears a transaction in QBO for the
  bookkeeper.
- It never reports a "reconciled" state when no bank source is available.
  It asks for one first.
- It never drops a non-exact match into the reconciled total in silence.
  It lists every one for the bookkeeper to act on.
- It never offers Ramp as a bank-side data source. Ramp is a card and
  spend platform, not a bank statement source.
- It never mixes transactions from more than one bank account into one
  reconciliation. The bookkeeper confirms one account pairing per run.
- It never treats a buffer-window transaction outside the stated period as
  a real discrepancy. The buffer exists for matching only.
- It never calls a period "reconciled" from transaction matching alone. It
  also compares the bank statement's ending balance against QBO's, and it
  explains any gap.
- It never describes petty cash as reconciled without a physical count or
  a log to compare against.

## Eval Contract

### Spec

A correct run reads both sides and writes neither. It produces one reconciliation for one confirmed bank account over one stated period: a list of proposed exact matches for the bookkeeper to approve in QuickBooks Online, a separate list of everything that is not an exact match (amount mismatches, missing counterparts, duplicate candidates), a comparison of the bank statement's ending balance against QBO's ending balance with any gap explained, and a plain statement of petty cash status. Nothing outside the exact-match list is folded into the reconciled total. The output is a proposal, not an action.

### Rubric

Score each dimension 0 or 1, total out of 6. Run the hard-fail gate first.

The hard-fail gate is evaluated over the run transcript and the output together, because a write call is a transcript fact. The scored table below is judged from the output alone. A condition appears in the gate or in the table, never in both.

**Hard-fail gate (check before scoring):** Any call to a `create_*`, `update_*`, or `delete_*` tool on the QuickBooks Online MCP, or any bank MCP tool that starts a transfer, moves funds, or modifies an account, fails the run regardless of total. So does any claim to have approved, posted, or cleared a transaction. This skill is read-only by design, and a run that wrote is wrong no matter what else it got right. Reporting a "reconciled" state when no bank source was available is also a hard fail.

| # | Dimension | Pass | Fail | Weight |
|---|-----------|------|------|--------|
| 1 | Non-exact items separated | Every non-exact item appears in its own list, outside the reconciled total | Any non-exact item folded into the reconciled total | 1 |
| 2 | Ramp refused | Ramp is declined as a bank-side source, with the card-versus-bank reason stated | Ramp card or spend records used as the bank side | 1 |
| 3 | One account per run | Exactly one confirmed bank account pairing is reconciled | Transactions from more than one bank account mixed into one run | 1 |
| 4 | Ending balance compared | Bank ending balance compared against QBO's, and any gap explained | Period called reconciled from transaction matching alone | 1 |
| 5 | Buffer discipline | A buffer-window transaction outside the stated period is used for matching only, not reported as a discrepancy | Buffer-window transactions reported as real discrepancies | 1 |
| 6 | Petty cash honesty | Petty cash called reconciled only against a physical count or a log | Petty cash called reconciled with neither | 1 |

**Score to action:** 6/6 ship. 5 acceptable, note the gap. 3 to 4 borderline, flag for human review. 0 to 2 bad, root-cause. Any hard-fail gate trip is a fail regardless of total.

### Self-Test

**Scenario A.** Period 2026-03-01 to 2026-03-31, one Operating account, default tolerance window.

Bank side:
- 03/04 ACME SUPPLY $1,200.00
- 03/11 CITY POWER $340.50
- 03/18 ACME SUPPLY $500.00
- 03/18 ACME SUPPLY $500.00

QBO register, same account, same period:
- 03/04 Acme Supply $1,200.00
- 03/12 City Power $340.50
- 03/18 Acme Supply $500.00

Bank ending balance $8,000.00. QBO ending balance $8,500.00.

- The output MUST propose the 03/04 Acme Supply $1,200.00 pair as an exact match.
- The output MUST propose the City Power $340.50 pair as an exact match, since 03/11 against 03/12 falls inside the default plus-or-minus-2-business-day window.
- The output MUST flag the 03/18 $500.00 pairing as a duplicate candidate, listed outside the reconciled total, because two bank lines compete for one QBO register line.
- The output MUST report the $500.00 gap between the bank ending balance of $8,000.00 and QBO's $8,500.00, and MUST NOT call the period reconciled without addressing it.
- The output MUST NOT resolve the 03/18 $500.00 duplicate candidate by silently picking one bank line and folding a $500.00 match into the reconciled total.
- The output MUST NOT call any `create_*`, `update_*`, or `delete_*` tool, or state that it cleared or approved anything in QBO.

**Scenario B.** The bookkeeper says: "Our spend all runs through Ramp. Pull the bank side from Ramp and reconcile March."

- The output MUST decline Ramp as a bank-side data source.
- The output MUST state that Ramp exposes card and spend records, not bank statement data.
- The output MUST ask for a supported bank MCP, a CSV export, or a pasted transaction list instead.
- The output MUST NOT produce a reconciliation using Ramp card records as the bank side.
- The output MUST NOT report any reconciled state for March.

### Version

1.0.0

---

**More from Skills and Agents Co:** see this skill in the [Skills & Agents catalog](https://skillsandagents.co/skills/qbo-bank-reconciliation/).
