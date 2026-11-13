# Design language

USE this file WHEN the user asks you to create, extend or change a design language, or WHEN SKILL.md section 1.2 sends you here. FOLLOW SKILL.md section 1 with it. TO review a design language, USE [review.md](review.md) section R3. A design language is the written set of colours, type, spacing, components and rules that gives a set of interfaces one look and behaviour.

The findings these rules depend on:

1. A design language makes building faster and more consistent when builders use it. It does not by itself make an interface easier to use.
2. Interfaces that models generate look alike in appearance and layout, far more than interfaces by different human designers.
3. People largely agree on what a colour or a typeface expresses. The agreement is a starting point: individuals differ, context changes the reading, and some intended qualities do not come through.
4. Agents often fail to follow design requirements they were given, including ones they stated themselves.
5. Sizes, ratios and scales for type and spacing, typeface pairing, and the form of the document rest on convention. The rules about them here are design choices.

## L1. Decide where it lives

ASK the user where the design language lives, or FOLLOW the project's convention for such documents. WRITE it with [../templates/design-language.md](../templates/design-language.md). IF you cannot write files, PUT it in your reply.

KEEP one source of truth: GIVE every value a name, and USE the same names in the document and in the code. WRITE values in tables, not in running text, because agents follow a structured specification more closely than prose. TREAT this as a guide, not a rule.

## L2. Find what it must express, and for whom

ASK the user for three to five qualities the interfaces must express, such as calm, precise or playful, and for interfaces they like and dislike ([build.md](build.md) section B1.1). IF the brief does not say who the AUDIENCE is, ASK: preferred colourfulness and density differ by country, education and age.

USE what colours and typefaces commonly express as a starting point for each quality. DO NOT assume the result expresses it. CHECK it in section L3.

## L3. Propose directions that depart from your default

BEFORE you propose anything, WRITE DOWN the palette, typeface and layout you would produce by default for this request. MAKE at least one direction depart from that default, in a way you can tie to a quality from section L2. REVIEW your directions against each other and REPLACE one that is a near copy of another. Asking for more randomness does not make directions differ. TREAT this as a guide, not a rule.

KEEP the structure of each direction familiar and simple, and PUT the difference into a few elements: people judge simple, typical-looking interfaces as appealing, within a fraction of a second. TREAT this as a guide, not a rule.

SHOW each direction on one real screen from the scenarios, with the same content ([build.md](build.md) section B1.2). ASK the user which qualities each direction expresses, not only which one they prefer. IF a quality does not come through, CHANGE the direction, not the user's answer.

## L4. Build the parts

### L4.1. Colour

- DEFINE colours by role: backgrounds, text, accents, borders, and states such as error and success.
- CHECK every pair of text colour and background colour you allow against SKILL.md section 2.2, and LIST the allowed pairs in the document.
- KEEP the colours that carry meaning to about five or fewer, and PAIR each with a label, an icon or a shape: people tell colours apart less reliably as their number grows. TREAT the number as a guide, not a rule.
- TREAT a dark variant as a choice. IF the design language has light and dark variants, DEFINE both and CHECK the pairs in each.

### L4.2. Type

- CHOOSE typefaces by the qualities from section L2. No typeface is the most legible for everyone, and pairing typefaces is taste. AVOID narrow letterforms for body text, which cost most for readers with low vision. TREAT this as a guide, not a rule.
- SET body size and line length by SKILL.md section 2.2.
- MAKE each heading level differ from the next by size, by about a fifth or more, and by weight where needed. TREAT this as a guide, not a rule.
- KEEP the set of sizes and weights small.

### L4.3. Spacing

DEFINE a small scale of spacing values and USE only those. KEEP density even (SKILL.md section 2.1).

### L4.4. Components

LIST only the components the scenarios need. FOR each one, DEFINE its states ([build.md](build.md) section B3) and its name and role for assistive technology (SKILL.md section 2.4).

## L5. Write the rules so builders can follow them

NAME components and sections with the words a builder would search for. FOR each rule, GIVE the reason, one example of correct use and one of wrong use. KEEP the document short: a rule earns its place only if a builder would otherwise choose differently.

## L6. Check what was built against it

AFTER building with a design language, DO NOT trust that you followed it. SEARCH the code for colours, sizes and spacing values that are not named in the document, and for components that duplicate a listed one. LOOK at the rendered screens side by side for differences between them, because checks of single elements miss problems that span a page.

REPLACE each stray value with a named one, or PROPOSE it as an addition (section L7).

## L7. Change it only with the user

The design language belongs to the user. PROPOSE each addition, change or exception, with the reason and where it applies. DO NOT change it silently to make a screen work. RECORD each accepted change in the document. WHEN a value changes, FIND and UPDATE its uses.
