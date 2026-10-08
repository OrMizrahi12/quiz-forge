# item_writer versions

Each version is measured with: python -m experiments.measure <version> 6
Claude Haiku 4.5, lessons L1.3, L2.1 and L3.2, 6 runs each, checked by
quizforge/validate.py. A few runs show a direction, not a rate.

## v4
One change from v3: rule 4 says how the quote is checked.
Why: v3's failed quotes joined sentences, cut words, or turned a table
row into a sentence.
Measured: pass 13/18; quote not in the lesson 4; scenario asks no question 3
Next: quote not in the lesson, one change at a time.

## v3
system.md as of Lesson 2.5, the baseline.
Measured: pass 11/18; quote not in the lesson 6; expected 2 questions, got 3 2

## v1, v2
The user-turn prompts of Lesson 2.1.
