# `/decide-better`

Helps you make a decision yourself, so the choice fits what matters to you and rests on your own judgement.

> **Should the decision method be a skill of its own?**
>
> 1. **Rules only**: add "name the main drawback" to the skills that recommend.
> 2. **A core skill**: one skill holds the method, and the others use it when you must choose.
>
> Which way do you lean, and why? Or skip this and see my recommendation.

*The decision that created this skill, in the form it asks: the options first, then your leaning before its view.*

## What it does

- **Separates your decisions from its own.** It makes the decisions about how to carry out your choice, and states them. It brings you the ones about your goals, money, time, people, or work you will maintain.
- **Asks which way you lean before giving its view**, unless you already said. You can skip, and it then stops asking.
- **Checks each option against what matters to you**, using the criteria you stated or the two or three you name.
- **Gives its recommendation with the main drawback.** If it agrees with your leaning, it gives the strongest case against it.
- **Asks instead of judging** when the options differ mainly in which of your values wins.

For example:

```
/decide-better move the blog to a static site or keep the CMS
```

## Reference

<details>
<summary><b>When to use it</b></summary>

- Before a decision you will live with, such as a plan, a tool, a job or a purchase.
- When you notice you are taking the agent's answer without weighing it.

Running it does not mean a long method. A small or easy-to-reverse decision ends with one recommendation and its drawback.

Other skills use it when you must choose, so you rarely need to call it yourself (see Works with below).

</details>

<details>
<summary><b>How to run it</b></summary>

- `/decide-better <decision>` helps with that decision.
- `/decide-better` with no argument helps with the decision in the current conversation.

If you say "just tell me", it gives its recommendation, the main reason and the main drawback, and stops.

</details>

<details>
<summary><b>What happens</b></summary>

1. **It names the decision and who owns it.** It makes the decisions that are its own and states them.
2. **It sizes the decision.** For a small, reversible or urgent one, it gives its recommendation, the main reason and the main drawback, and stops.
3. **It lays out the options**, including keeping things as they are, with what is likely to happen and what is unknown. It does not give its view yet.
4. **It asks which way you lean, and why**, and for the two or three things that matter most if you have not said. You can skip.
5. **It compares the options against your criteria**, with the evidence in each cell and unknowns marked.
6. **It gives its view.** It recommends one option, with the main reason and the main drawback. If it agrees with you, it gives the strongest case against your leaning; if it disagrees, it says why once, with the evidence. You decide.
7. **For a choice between your values**, it shows what each option costs on each value and asks questions instead of recommending.

When you look back at a past decision, it judges it by what was known at the time, not by how it turned out.

</details>

<details>
<summary><b>What you get</b></summary>

- The options, with likely outcomes and unknowns.
- A comparison of the options against your criteria.
- A recommendation with its main reason and main drawback, or questions when the choice is between your values.

</details>

<details>
<summary><b>Works with</b></summary>

It calls:

- [`/ask-better`](ask-better.md) for its questions.
- [`/write-better`](write-better.md) for the words.

It is called by:

- [`/ask-better`](ask-better.md) when a question asks you to make a decision that is yours.
- [`/write-better`](write-better.md) when a text is for a decision you make.
- [`/code-better`](code-better.md) when it shows you design decisions before building.
- [`/review-better`](review-better.md) when you must choose between fixes.

</details>

<details>
<summary><b>What it needs</b></summary>

- **Asking you.** Without it, it gives its view after the comparison and says it is one input to your decision.

</details>
