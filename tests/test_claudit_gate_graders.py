"""The #193 gate graders in bin/claudit-eval (`gate`): rule 6 (no principles skill anywhere in an f19 report) and
rule 4 (python-sdk documentation-page skills, quickstop's two stale history lines).

Each grader has a false-negative pass (real phrasings, several from recorded reports) and an attacker pass:
negations on the same line, rhetorical questions, qualifiers that reverse an allowed form, and imperatives.
"""
import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_claudit_eval import ce  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REAL = ROOT / 'docs/acceptance/claudit-eval-baselines/192-real-repos'

# Proposals, anywhere in a report. The first three are Claudit 4.2.0's f19 notes from the #192 gate (3 of 3 runs);
# the rest are the O1 grader's proposal controls (review M4, N5, L-b) and the plain arm's phrasings.
PROPOSALS = [
    '- Optional: add a skill for `docs/principles.md`. CLAUDE.md:10 links it, and it has 7 steps. Create '
    '`.claude/skills/principles/SKILL.md` with `name` and `description` frontmatter that follows those steps, and keep '
    'the doc as the source.',
    '- Optional: `CLAUDE.md:10` links `docs/principles.md`, a 7-step procedure doc. You could turn it into a skill at '
    '`.claude/skills/principles/SKILL.md`, with name and description frontmatter that follows the steps and links the '
    'doc as the source. This is only worth doing if you want it loaded on demand rather than read each time.',
    '- **Optional: turn `docs/principles.md` into a skill.** `CLAUDE.md:10` links it from the loaded instructions, and '
    'it has 7 steps.',
    'Consider creating a skill from the principles.',
    'Consider making the principles a skill.',
    '`docs/principles.md` could be packaged as a skill.',
    'The principles in `docs/principles.md` would work well as a skill.',
    'A `principles` skill would load only when needed.',
    '`docs/principles.md` is always loaded; a skill would cut that.',
    'Convert to a skill: `docs/principles.md`.',
    '`docs/principles.md` would be a good fit for a skill.',
    'Turning the principles into a slash command would help.',
    'A skill for the principles would help.',
    'Turn `docs/principles.md` into a skill.',
    'Moving `docs/principles.md` into `.claude/skills/principles/SKILL.md` saves context.',
    '`docs/principles.md` deserves its own skill.',
    '| `docs/principles.md` | 7 principles | Make it a skill |',
    '1. **Load the principles on demand** (Alignment, effort S)\n   Problem: they load every session.\n'
    '   Change: create `.claude/skills/principles/SKILL.md`.',
]
# Attacker pass: forms that slip a proposal past a looser grader.
ATTACKS = [
    'Why not make `docs/principles.md` a skill?',  # rhetorical question
    "Wouldn't a skill for the principles help?",
    'How about a `/principles` slash command?',
    'Nothing else needs fixing. Make `docs/principles.md` a skill.',  # negation earlier on the same line
    'No skill is needed for the principles yet, but a skill for them would still help.',  # reversing qualifier
    "The principles aren't a procedure, so a skill isn't needed today; add one when the list grows.",
    'Skills are for procedures, and the principles would make a good one: turn them into a skill.',
    'A skill for the principles is not overkill.',  # a negated rejection
    'Rather than leaving it as prose, turn `docs/principles.md` into a skill.',  # "rather than" governs prose
    '`docs/principles.md` is a list. Optionally, wrap it in a skill so it loads on demand.',  # back-reference
    'Is a skill for the principles worth it? Yes: add one.',
    '- **Also worth knowing:** the principles could become a skill later.',
    # Review round 1, M2: a rejection reversed later in the sentence.
    "A principles skill isn't necessary today, but worth adding later.",
    'A skill for the principles is unnecessary right now, though you could add it later.',
    "Don't hesitate to turn the principles into a skill.",  # a negation that urges
    'Nothing else is wrong and a skill for the principles would help.',  # a negation whose scope ends at "and"
    'Declined: nothing. Add a skill for `docs/principles.md`.',  # a decline line, then a proposal
    # Review round 2, M5: a named skill to create is still a principles skill (f19 has no skills).
    'Add a `go-style` skill from docs/principles.md.',
    'Turn docs/principles.md into a `team-values` skill.',
    'Optional: create a `design-rules` skill that loads docs/principles.md on demand.',
    '- Optional: a `/guidelines` slash command could load docs/principles.md.',
    'Run the `review` skill and add a skill for docs/principles.md.',
    'Like the `review` skill, docs/principles.md would work well as a skill.',
    'Extend the `review` skill with a principles skill.',
    # Review round 2, L4: an urging double negation.
    'I would not hesitate to turn the principles into a skill.',
    "I wouldn't skip a skill for the principles.",
]
# Recorded skill proposals for another doc (#184 gate: tallyho's release procedure, quickstop's SDLC doc), with
# `docs/principles.md` in place of that doc: the shapes Claudit has actually written.
RECORDED = [
    '- Optional: add a skill for `docs/principles.md`, which `CLAUDE.md:10` already links. Create '
    "`.claude/skills/principles/SKILL.md` with `name` and `description` frontmatter that follows the doc's steps and "
    'links back to it. The doc stays the source.',
    '- Optional: add a skill for `docs/principles.md`. `CLAUDE.md:10` already links it from the loaded instructions. '
    "You could create `.claude/skills/principles/SKILL.md` with `name` and `description` frontmatter that follows the "
    "doc's steps and links back to it, so the doc stays the source.",
    '2. **Add a skill for docs/principles.md** (Coverage, effort M)\n   Problem: `docs/principles.md` has 7 numbered '
    'steps, but no skill exists and nothing loaded links to it.\n   Change: Create '
    '`.claude/skills/principles/SKILL.md` with `name` and `description` frontmatter. It should follow the steps in '
    '`docs/principles.md`, keep that doc as the source and link to it.',
    '3. **Turn the principles into a skill** (Coverage, effort M)\n   Problem: `docs/principles.md` has 7 numbered '
    'steps, and agents follow them. No skill exists.\n   Why: a skill makes them invocable by name.',
    '   Change: Create `.claude/skills/principles/SKILL.md` with `name` and `description` frontmatter. Make it follow '
    'the steps in `docs/principles.md`, keep the doc as the source, and link it.',
    '   Why: The principles are a repeatable procedure that agents would carry out. A skill loads it on demand.',
]
# Correct statements: none proposes a skill for the principles.
SAFE = [
    'Keep `docs/principles.md` as is; skills are for procedures.',
    '`docs/principles.md` reads as rules, unlike the release procedure in `docs/release.md`.',
    '`docs/principles.md` is a declarative list; a skill would add nothing.',
    'The principles are fine as text; a skill would be overkill.',
    '`docs/principles.md` is a list of principles, not a procedure, so it needs no skill.',
    'No procedure needs a skill: `docs/principles.md` holds standing principles.',
    "Don't turn `docs/principles.md` into a skill.",
    'No skill is needed for the principles.',
    'Rather than a skill, keep the principles in `docs/principles.md`.',
    "The principles aren't a procedure, so a skill is the wrong fit.",
    'Skills suit procedures; the principles are a list.',
    'None of this needs a skill, including `docs/principles.md`.',
    '`docs/principles.md` is fine. Add a skill for `docs/release.md`.',  # a skill for another file
    'Import the principles with `@docs/principles.md` so they load every session.',
    '- `docs/principles.md` holds standing principles, so no skill is proposed for it.',
    # Review round 1, M2: real rejections and another skill.
    "Don't turn the principles list into a skill; it isn't a procedure.",
    'There is no need to turn the principles into a skill.',
    'I considered a skill for docs/principles.md and decided against it.',
    'Declined: a skill for docs/principles.md (it states values, not steps).',
    'Run the `review` skill; it reads docs/principles.md.',
    'No skill is needed for the principles, now or later.',
    # Review round 2, M6: a later clause about something else doesn't reverse the rejection.
    'No skill is needed for docs/principles.md; consider headings later.',
    'No skill needed for docs/principles.md, though you should add a test later.',
    'A skill would add nothing for docs/principles.md, though the doc could use headings later.',
    # A clause that runs or uses an existing skill, with no creation act.
    'Use the `review` skill when a change touches docs/principles.md.',
]
# Recorded lines about the principles that propose no skill (#192 plain and doctor-combined f19 reports).
RECORDED_SAFE = [
    '- `CLAUDE.md:10` says `docs/principles.md` holds for every change, but it only mentions the path. Claude reads it '
    'only if it decides to.',
    "- Once the principles are loaded, this is the kind of gap Claude will start flagging. Fix it so the rule isn't "
    'already violated.',
    "- The file is 9 lines, so import it with `@docs/principles.md`. That way it's in context every session.",
    '- `CLAUDE.md` says the principles "hold for every change", but it only names the path. Claude has to decide to '
    'open `docs/principles.md`, and it may not.',
    '- Add a "conventions" line to `CLAUDE.md`, such as "table-driven tests" and "new exported funcs need an Example". '
    'The principles already imply these.',
    '**1. Import the principles file in `CLAUDE.md`.**',
    '1. **`docs/principles.md` may not load.** `CLAUDE.md` mentions it in prose only, so Claude has to decide to open it. '
    'The file says it holds "for every change", so import it with `@docs/principles.md`. It\'s only 7 lines.',
]


def report(body, where='## Also worth knowing'):
    return ('# Claudit: quillcount\n\n## Top changes\n\n1. **Install a code-intelligence plugin** (Coverage, effort S)\n'
            '   Problem: no LSP.\n\n%s\n\n%s\n\n---\nClaudit 4.3.0; audited commit %s\n' % (where, body, 'a' * 40))


class PrinciplesSkill(unittest.TestCase):
    def test_proposals_fail_anywhere(self):
        for where in ('## Also worth knowing', '## Top changes', '## From /doctor prompt-audit', ''):
            for body in PROPOSALS + ATTACKS + RECORDED:
                with self.subTest(where=where, body=body):
                    self.assertTrue(ce.principles_skill_units(report(body, where)), body)

    def test_correct_statements_pass(self):
        for body in SAFE + RECORDED_SAFE:
            with self.subTest(body=body):
                self.assertEqual(ce.principles_skill_units(report(body)), [], body)

    def test_a_skill_for_another_file_beside_the_principles_passes(self):
        text = report('- `docs/principles.md` holds standing rules.\n- Add a skill for `docs/release.md`; it has 6 steps.')
        self.assertEqual(ce.principles_skill_units(text), [])

    def test_regrade_of_the_192_reports(self):
        """Control: Claudit 4.2.0 offered a principles skill in 3 of 3 #192 f19 runs; the plain prompt never did."""
        runs = Path.home() / 'factory/retained/quickstop-192/results/gate-b3004cd'
        if not runs.is_dir():
            self.skipTest('the #192 retained results are not on this machine')
        for arm, expected in (('claudit', True), ('plain', False)):
            reports = sorted((runs / ('%s-f19-declarative-list' % arm) / 'reports').glob('*.md'))
            self.assertEqual(len(reports), 3)
            for path in reports:
                with self.subTest(report=path.name, arm=arm):
                    self.assertEqual(bool(ce.principles_skill_units(path.read_text())), expected)


def plan(*titles):
    return report('- Nothing else.').replace('1. **Install a code-intelligence plugin** (Coverage, effort S)\n'
                                             '   Problem: no LSP.', ''.join(
        '%d. **%s** (Coverage, effort M)\n   Why: because agents follow it.\n\n' % (n, t)
        for n, t in enumerate(titles, 1)))


class DocSkills(unittest.TestCase):
    def test_any_skill_proposal_for_a_page_counts_each_page(self):
        # Review round 1, M1: the structure (a skill proposal whose target is a doc page), not one phrasing.
        for title, pages in (('Turn `docs/testing.md` into a skill', ['docs/testing.md']),
                             ('Add skills for docs/testing.md and docs/release.md', ['docs/testing.md',
                                                                                     'docs/release.md']),
                             ('Add a `testing` skill from docs/testing.md', ['docs/testing.md']),
                             ('Make `docs/api/reference.md` a skill', ['docs/api/reference.md']),
                             ('Package `docs/deploy.md` as a slash command', ['docs/deploy.md']),
                             # Review round 2, L4.
                             ('Give docs/testing.md its own skill', ['docs/testing.md']),
                             ('Skill: docs/testing.md', ['docs/testing.md'])):
            with self.subTest(title=title):
                self.assertEqual([p for p, _, _ in ce.doc_skill_items(plan(title))], pages)
        self.assertFalse(ce.doc_skills_pass(ce.doc_skill_items(plan('Make `docs/api/reference.md` a skill'))))

    def test_items_that_propose_no_skill_for_a_page(self):
        for title in ('Fix the stale facts in docs/x.md', 'Keep each repeated rule in one place',
                      'Fix the dangling `docs/architecture.md` reference before changing the skill',
                      "Don't add a skill for docs/testing.md", 'Hide .claude/skills/a/SKILL.md from the skill listing'):
            with self.subTest(title=title):
                self.assertEqual(ce.doc_skill_items(plan(title)), [])

    def test_recorded_gate_reports(self):
        """The 4.0.1 gate's f1 reports title the change "Turn the release procedure into a skill" and name the page in
        its Problem line; the f2 reports mention "the skill" in a stale-reference change and propose none."""
        reports = ROOT / 'tests/claudit_gate_reports'
        for path in sorted(reports.glob('*.md')):
            with self.subTest(report=path.name):
                pages = [p for p, _, _ in ce.doc_skill_items(path.read_text())]
                self.assertEqual(pages, ['docs/release-procedure.md'] if path.name.startswith('f1-') else [])

    def test_one_page_needs_a_reason(self):
        text = plan('Add a skill for RELEASE.md').replace('   Why: because agents follow it.\n', '   Problem: x.\n')
        self.assertEqual(ce.doc_skill_items(text), [('RELEASE.md', False, False)])
        self.assertFalse(ce.doc_skills_pass(ce.doc_skill_items(text)))
        self.assertTrue(ce.doc_skills_pass(ce.doc_skill_items(plan('Add a skill for RELEASE.md'))))

    def test_counts_documentation_page_skills_in_top_changes(self):
        text = report('- Optional: add a skill for `docs/x.md`.', '## Also worth knowing').replace(
            '1. **Install a code-intelligence plugin** (Coverage, effort S)',
            '1. **Add a skill for docs/whats-new.md** (Coverage, effort M)\n\n'
            '2. **Add a skill for i18n/de/pages/whats-new.md** (Coverage, effort M)\n\n'
            '### 3. **Add a skill for `docs/reference/cli.md`**')
        self.assertEqual([i[:2] for i in ce.doc_skill_items(text)], [('docs/whats-new.md', False),
                                                                    ('i18n/de/pages/whats-new.md', True),
                                                                    ('docs/reference/cli.md', True)])

    def test_recorded_python_sdk_reports(self):
        items = ce.doc_skill_items((REAL / 'python-sdk-claudit.md').read_text())
        self.assertEqual(len(items), 6)  # 4.2.0: six of seven changes, four of them translations
        self.assertEqual(sum(page for _, page, _ in items), 4)
        self.assertFalse(ce.doc_skills_pass(items))
        self.assertEqual(ce.doc_skill_items((REAL / 'python-sdk-doctor-combined.md').read_text()), [])

    def test_one_procedure_skill_and_notes_outside_the_plan_pass(self):
        text = report('- Optional: add a skill for `i18n/de/pages/x.md`.').replace(
            'Install a code-intelligence plugin', 'Add a skill for RELEASE.md')
        self.assertEqual([i[:2] for i in ce.doc_skill_items(text)], [('RELEASE.md', False)])


class HistoryLines(unittest.TestCase):
    FOUND = [
        # doctor-combined on quickstop (#192): a numbered finding with Location bullets.
        '**1. History narrative in the verification section** (medium)\n- **Location:** `docs/repository.md:42-43`\n'
        '- **Evidence:** "The initial compatibility run also passed on Python 3.9.6."\n\n'
        '**2. Retired-hook archaeology** (medium)\n- **Location:** `docs/repository.md:63-67`\n',
        '- `docs/repository.md:42` records a past event ("The initial compatibility run also passed on Python 3.9.6").\n'
        '- `docs/repository.md:64` is stale history: "Repository push hooks and Claude shell-match hooks have been '
        'retired".',
        '| `docs/repository.md:43` | history narrative: initial compatibility run | rewrite |\n'
        '| `docs/repository.md:65` | outdated: retired push hooks | rewrite |',
    ]
    NOT_FOUND = [
        # Claudit 4.2.0 on quickstop: the hooks line as a decline, not as stale history.
        '- **Hooks** (`docs/repository.md:64`): "Repository push hooks and Claude shell-match hooks have been retired; '
        'clean-checkout evidence is the verification gate."',
        '- `docs/repository.md:42` (the 3.9.6 compatibility run) is not stale; keep it.\n'
        '- `docs/repository.md:64` (retired push hooks) is not outdated.',
        '- The history in `CHANGELOG.md` mentions Python 3.9.6 and retired hooks.',  # another file
        # Review round 1, L1: a decline is not a finding.
        '- Declined: docs/repository.md lines about retired hooks and the 3.9.6 compatibility run are history, kept on '
        'purpose.',
        '## Declined by the project\n\n- **Hooks** (`docs/repository.md:64`): history, "have been retired".\n'
        '- `docs/repository.md:42`: a stale record of the 3.9.6 compatibility run.',
    ]

    def test_fix_on_purpose_is_not_a_keep(self):
        # Review round 2, L4: only a keep ("kept on purpose") sets a line aside.
        text = report('- `docs/repository.md:42`: the 3.9.6 compatibility run note is history. Fix it on purpose.')
        self.assertEqual(ce.history_lines(text), ['compatibility-run'])

    def test_both_lines_found(self):
        for body in self.FOUND:
            with self.subTest(body=body[:60]):
                self.assertEqual(ce.history_lines(report(body)), ['compatibility-run', 'retired-hooks'])

    def test_declines_negations_and_other_files_do_not_count(self):
        for body in self.NOT_FOUND:
            with self.subTest(body=body[:60]):
                self.assertEqual(ce.history_lines(report(body)), [])

    def test_recorded_quickstop_reports(self):
        self.assertEqual(ce.history_lines((REAL / 'quickstop-doctor-combined.md').read_text()),
                         ['compatibility-run', 'retired-hooks'])
        self.assertEqual(ce.history_lines((REAL / 'quickstop-claudit.md').read_text()), [])


if __name__ == '__main__':
    unittest.main()
