# design-better priorities

The categories that eval results for design-better are grouped by, highest first. A change may lose in a lower category where it gains in a higher one. See section 10 of `evals/PRINCIPLES.md`.

1. **People can use it**: the interface is checked by operating it for the people it serves, and findings are about what stops them.
   - Rules: `walk-every-scenario-after-build`, `findings-from-operating`, `check-meaning-not-presence`, `structure-before-defects`, `do-not-simulate-people`.
   - Cases: `acceptance-walk`, `audit-operates-interface`, `audit-label-meaning`, `audit-structure-first`, `no-simulated-persona`.
2. **The user decides**: the user's direction, design language and decisions come first, and questions are few and costly to get wrong.
   - Rules: `ask-users-direction-first`, `review-chosen-direction`, `ask-few-costly-questions`, `ask-what-it-expresses`, `keep-design-language`, `audit-report-only`.
   - Cases: `ask-direction-first`, `direction-review-before-build`, `cancel-subscription-questions`, `language-ask-qualities`, `muted-text-contrast`, `audit-report-only`.
3. **Honest hand-back**: says what was walked and how, and does not claim that people can use it.
   - Rules: `report-walked-not-usable`.
   - Cases: `handback-three-things`.
4. **Design craft**: the design, directions and build follow the skill's design rules.
   - Rules: `write-design-with-requirements`, `rough-directions-differ`, `one-meaning-per-colour`, `check-built-against-language`, `show-every-screen-size`, `small-change-skips-process`.
   - Cases: `design-before-build`, `directions-differ-in-structure`, `colour-one-meaning`, `language-stray-values`, `canvas-every-brief-size`, `small-label-change`.

Honest hand-back has 1 case, so it is not a category in the results.
