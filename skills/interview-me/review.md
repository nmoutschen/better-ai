# Interview: how the user reviews (`review-for`)

FOLLOW the steps in [SKILL.md](SKILL.md) around this interview: prepare (section 1), how to ask (section 2), write the output (section 3) and report (section 4).

## 1. Material to collect

ASK for a piece of work the user reviewed, with the comments they gave, such as a pull request, a marked-up draft, or a feedback message.

## 2. Walk through a real review

ASK the user to describe how they reviewed the work: what they looked at first, what made them comment, and what made them approve or reject it. LET them answer without interrupting.

THEN, FOR each of their comments, ASK:

1. Whether it had to be fixed before approval, or was a suggestion.
2. What they saw that made them write it.
3. What a version that needed no comment would have looked like.

ASK what they did not comment on and why. Criteria a reviewer applies but does not state often show up in what they let pass.

## 3. Compare two samples

SHOW two versions of a small piece of work in the user's domain, such as two functions, two paragraphs, or two plans. TAKE them from the user's material or from your own work in this conversation when possible. MAKE them differ on one point that the walk-through did not settle.

ASK which one they would approve, which comment they would write on the other, and whether that comment blocks approval.

## 4. Separate blocking criteria from preferences

LIST the criteria found so far. ASK the user to mark each one as blocking, meaning the work is not approved until it is fixed, or as a preference. DO NOT ask them to rate criteria on a scale: a scale lets every criterion look important.

## 5. Output

FOLLOW [templates/review-for.md](templates/review-for.md). A criterion earns its place only when it changes what an agent already following `/code-better` would check in a code review.

SAVE it as the skill `review-for-<name>`, in a folder where the user's harness loads personal skills, or in a project's skills folder if the guide is for one project.
