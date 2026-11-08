---
name: show-better
description: Helps an AI agent decide when to show information as a table, chart or diagram instead of prose, choose the format by what the reader must do, design it so it is read correctly, and check generated chart or diagram code before showing it.
argument-hint: "[CONTENT]"
---

# Show Better

Instructions on when and how to present information visually.

IF invoked without argument, use these instructions on your previous output: add, change or remove its tables, charts and diagrams.
IF invoked with content or data as argument, use these instructions to present it.

Being invoked does NOT mean a visual is needed. These instructions can end with prose.

## Principles

1. A relevant graphic helps readers understand and learn from text. Decoration does not help, and irrelevant details can hurt.
2. A diagram helps when the content is about relations: it groups related items in space, so the reader searches less.
3. Most rules for choosing between prose, a table and a chart are design guidance, not experiments. No controlled study tests visual answers from AI assistants.
4. Generated chart code often fails silently: it calls the wrong function, or misreads the data and plots wrong values that still look plausible.

## 1. Know the reader and the medium

### 1.1. Name the reader's task

IDENTIFY what the reader must do with the information:

1. Take in one or two numbers.
2. Look up or compare exact values.
3. See a trend or pattern across many values.
4. Understand relations, structure or a process.
5. Compare several items on several aspects.

IF the content serves several tasks, CHOOSE the one that serves the user's GOAL. USE `/write-better` to name the GOAL if available.

### 1.2. Know what will render

IDENTIFY where the output will be read, and what it can display:

- **Terminal or plain text**: monospace text only. Markdown may show as raw symbols. The width may be about 80 characters.
- **Markdown chat**: tables, lists and code blocks. Mermaid and images only if the client renders them.
- **HTML page or artifact**: anything, including interactive charts.
- **File** (document, image, notebook): what that format and its viewer support.

IF you do not know, ASSUME the simplest medium the context allows. DO NOT produce a format the reader cannot render.

## 2. Choose the format

USE the reader's task from section 1.1:

| Reader's task | Format |
|---|---|
| Take in one or two numbers | Prose |
| Look up or compare exact values | Table |
| See a trend or pattern across many values | Chart, with its data in a table nearby |
| Understand relations, structure or a process | Diagram |
| Compare several items on several aspects | Table |

USE prose by default. ADD a visual only when it does something prose cannot do for that task.

DO NOT use a chart when a table is enough. DO NOT turn a whole answer into one large diagram: readers found whole-answer diagrams intimidating. SHOW the part that has the relations, and keep the rest as prose.

FOLLOW the conventions of the reader's field when they differ, such as charts for regression results.

## 3. Design the visual

### 3.1. For every visual

PUT labels and explanations next to what they describe: label lines and bars directly, and put a diagram's explanation beside it, not paragraphs away. This matters most for complex material.

DO NOT add decoration: images, icons, colours or effects that carry no information.

STATE the visual's main point in one sentence of text next to it.

DO NOT use colour as the only signal. ADD a label, pattern or shape as well. GIVE the parts the reader needs at least 3:1 contrast against what is next to them.

GIVE every image, chart and diagram a text description: one short line that names what it shows, and a longer description of its essential information. IN Markdown or text, the main-point sentence and the data table can serve as these.

### 3.2. Tables

PUT units in column headers. ALIGN numbers so they can be compared. ORDER rows by what the reader will look for, such as size or date, not by the order you found them.

IN a terminal or narrow medium, KEEP tables to a few short columns. IF a table is too wide, PRESENT each row as a short list of fields instead.

### 3.3. Charts

ENCODE the main comparison as position on a shared scale, such as bars from one baseline or points on one axis, rather than area, angle or colour intensity. TREAT this as a guide, not a rule: how well an encoding works depends on the task and the data.

START a bar chart's value axis at zero. IF the chart's purpose requires a different start, STATE it on the chart.

PUT the chart's data in a table below it, or make the values readable on the chart.

IF the user or project has a style guide for charts or colours, FOLLOW it.

### 3.4. Diagrams

GIVE each arrow and line one meaning, and STATE it in a label or legend. DO NOT use several arrow styles unless each style has its own stated meaning.

KEEP one direction of flow: top to bottom or left to right. LEAVE room for labels on branches.

KEEP text in boxes short. PUT longer explanations next to the diagram.

FOR a reader new to the topic, LABEL the parts in the diagram itself. FOR an expert, a less labelled diagram may be enough. The evidence for this difference is weak, so KEEP the labels when unsure.

### 3.5. In a terminal or plain text

USE a Markdown table only when the client renders Markdown or the raw table still reads clearly.

FOR a small structure or flow, USE a plain-text diagram in a code block. KEEP it narrow, and CHECK that its characters line up in a monospace font.

USE Mermaid or similar diagram code only when it will be rendered, or when the user will paste it into a tool that renders it. Raw Mermaid is hard to read once it is complex.

## 4. Check the visual before showing it

FOR a chart or diagram you generate with code:

1. BEFORE writing the code, SUMMARISE the data: its fields, types, ranges and row count. WRITE the code from that summary, not from field names alone.
2. RUN the code. FIX any error. DO NOT show code you have not run, unless you cannot run it; THEN SAY so.
3. CHECK the plotted values against the source data: at least the largest, the smallest, and any value the main point depends on.
4. LOOK at the rendered output if you can, and CHECK labels, overlaps, axis start and legend.

FOR a table, CHECK each value against its source, and CHECK that totals and percentages add up.

FOR a diagram, CHECK that every box and arrow matches the text it illustrates, and that nothing in the text contradicts it.

REPORT only checks you performed.
