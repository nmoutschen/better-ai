---
name: language
description: Use to create, extend or change a design language, or when SKILL.md step 1 finds none for work that covers more than one screen.
---

# Mode: language

FOLLOW these steps in order. The general rules of SKILL.md apply throughout. TO review a design language, USE [audit.md](audit.md). A design language is the written set of colours, type, spacing, components and rules that gives a set of interfaces one look and behaviour.

The findings these rules depend on:

1. A design language makes building faster and more consistent when builders use it. It does not by itself make an interface easier to use.
2. Interfaces that models generate look alike in appearance and layout, far more than interfaces by different human designers.
3. People largely agree on what a colour or a typeface expresses. The agreement is a starting point: individuals differ, context changes the reading, and some intended qualities do not come through.
4. Agents often fail to follow design requirements they were given, including ones they stated themselves.
5. Sizes, ratios and scales for type and spacing, typeface pairing, and the form of the document rest on convention. The rules about them here are design choices.

## 1. Decide where it lives

ASK the user where the design language lives, or FOLLOW the project's convention for such documents. READ [../templates/design-language.md](../templates/design-language.md) and WRITE it in its format.

KEEP one source of truth: GIVE every value a name, and USE the same names in the document and in the code. WRITE values in tables, not in running text, because agents follow a structured specification more closely than prose. TREAT this as a guide, not a rule.

## 2. Find what it must express, and for whom

ASK the user what the interfaces must express, in their own words, and for interfaces they like and dislike. DO NOT suggest example qualities: examples narrow what people consider. IF the user has no words for it, DERIVE the qualities from the interfaces they like and dislike, and CONFIRM them with the user. IF the brief does not say who the AUDIENCE is, ASK: preferred colourfulness and density differ by country, education and age.

USE what colours and typefaces commonly express as a starting point for each quality. DO NOT assume the result expresses it. CHECK it in step 3.

## 3. Propose directions that depart from your default

BEFORE you propose anything, WRITE DOWN the palette, typeface and layout you would produce by default for this request. MAKE at least one direction depart from that default, in a way you can tie to a quality from step 2. REVIEW your directions against each other and REPLACE one that is a near copy of another. Asking for more randomness does not make directions differ. TREAT this as a guide, not a rule.

KEEP the structure of each direction familiar and simple, and PUT the difference into a few elements: people judge simple, typical-looking interfaces as appealing, within a fraction of a second. TREAT this as a guide, not a rule.

SHOW each direction on one real screen from the scenarios, with the same content, by the general rule [Show versions on one page](../SKILL.md#show-versions-on-one-page). ASK the user which qualities each direction expresses, not only which one they prefer. IF a quality does not come through, CHANGE the direction, not the user's answer.

## 4. Build the parts

### 4.1. Colour

- DEFINE colours by role: backgrounds, text, accents, borders, and states such as error and success.
- CHECK every pair of text colour and background colour you allow against the [Design rules](../SKILL.md#design-rules), and LIST the allowed pairs in the document.
- KEEP the colours that carry meaning to about five or fewer, and PAIR each with a label, an icon or a shape: people tell colours apart less reliably as their number grows. TREAT the number as a guide, not a rule.
- TREAT a dark variant as a choice. IF the design language has light and dark variants, DEFINE both and CHECK the pairs in each.

### 4.2. Type

- CHOOSE typefaces by the qualities from step 2. No typeface is the most legible for everyone, and pairing typefaces is taste. AVOID narrow letterforms for body text, which cost most for readers with low vision. TREAT this as a guide, not a rule.
- SET body size and line length by the [Design rules](../SKILL.md#design-rules).
- MAKE each heading level differ from the next by size, by about a fifth or more, and by weight where needed. TREAT this as a guide, not a rule.
- KEEP the set of sizes and weights small.

### 4.3. Spacing

DEFINE a small scale of spacing values and USE only those. KEEP density even.

### 4.4. Components

LIST only the components the scenarios need. FOR each one, DEFINE its states, such as empty, loading, error and success, and its name and role for assistive technology.

## 5. Write the rules so builders can follow them

NAME components and sections with the words a builder would search for. FOR each rule, GIVE the reason, one example of correct use and one of wrong use. KEEP the document short: a rule earns its place only if a builder would otherwise choose differently.

## 6. Check what was built against it

AFTER building with a design language, DO NOT trust that you followed it. SEARCH the code for colours, sizes and spacing values that are not named in the document, and for components that duplicate a listed one. LOOK at the rendered screens side by side for differences between them, because checks of single elements miss problems that span a page.

REPLACE each stray value with a named one, or PROPOSE it as an addition (step 7).

## 7. Change it only with the user

The design language belongs to the user. PROPOSE each addition, change or exception, with the reason and where it applies. DO NOT change it silently to make a screen work. RECORD each accepted change in the document. WHEN a value changes, FIND and UPDATE its uses.
