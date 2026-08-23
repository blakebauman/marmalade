# themeVariables reference

Set with `"theme": "base"`. Hex values only. Mermaid derives unset variables from
the ones you do set, so start with the roots and only add specifics when a
derived value is wrong.

## Roots — set these first

| Variable | Controls |
| :-- | :-- |
| `darkMode` | Boolean. Flips Mermaid's derivation math toward light-on-dark |
| `background` | Canvas behind the diagram |
| `fontFamily` | Global font stack |
| `fontSize` | Base size, e.g. `"15px"` |
| `primaryColor` | Root fill. Most other colors derive from this |
| `primaryTextColor` | Text on primary fills |
| `primaryBorderColor` | Border on primary fills |
| `secondaryColor` / `tertiaryColor` | Second and third fills, with matching `*TextColor` and `*BorderColor` |
| `lineColor` | Default edge color |
| `textColor` | Text outside nodes |
| `noteBkgColor` / `noteTextColor` / `noteBorderColor` | Note callouts |

## Flowchart

| Variable | Controls |
| :-- | :-- |
| `mainBkg` | Node fill |
| `nodeBorder` | Node stroke |
| `nodeTextColor` | Label text inside nodes |
| `clusterBkg` | `subgraph` background |
| `clusterBorder` | `subgraph` border |
| `defaultLinkColor` | Edge color when not overridden |
| `edgeLabelBackground` | Chip behind an edge label — set to the page background or labels sit on a mismatched patch |
| `titleColor` | Diagram title |

## Sequence

| Variable | Controls |
| :-- | :-- |
| `actorBkg` / `actorBorder` / `actorTextColor` | Participant boxes |
| `actorLineColor` | Vertical lifelines |
| `signalColor` / `signalTextColor` | Message arrows and their text |
| `labelBoxBkgColor` / `labelBoxBorderColor` / `labelTextColor` | `alt` / `loop` label boxes |
| `loopTextColor` | Text inside loop blocks |
| `activationBkgColor` / `activationBorderColor` | Activation bars |
| `sequenceNumberColor` | Text of auto-numbered messages |

## Gantt

`sectionBkgColor`, `altSectionBkgColor`, `sectionBkgColor2`, `taskBkgColor`,
`taskBorderColor`, `taskTextColor`, `taskTextLightColor`, `taskTextOutsideColor`,
`taskTextClickableColor`, `activeTaskBkgColor`, `activeTaskBorderColor`,
`doneTaskBkgColor`, `doneTaskBorderColor`, `critBkgColor`, `critBorderColor`,
`gridColor`, `todayLineColor`.

## Pie and series

`pie1` … `pie12` set the slice sequence, and are also used by some other
series-based diagrams. Set at least the first four or Mermaid falls back to
derived colors that rarely match a brand. `pieTitleTextSize`, `pieTitleTextColor`,
`pieSectionTextColor`, `pieOpacity` control the rest.

## Error state

`errorBkgColor`, `errorTextColor` — shown when Mermaid fails to parse. Worth
theming: it appears in your docs when something breaks.

## Diagram-level config (siblings of `themeVariables`)

These are not colors; they sit at the top level of the config file.

```json
{
  "flowchart": { "curve": "basis", "htmlLabels": true, "padding": 12, "nodeSpacing": 50, "rankSpacing": 50 },
  "sequence": { "useMaxWidth": true, "showSequenceNumbers": false, "mirrorActors": true, "wrap": false },
  "er": { "useMaxWidth": true, "layoutDirection": "TB", "minEntityWidth": 100 },
  "gantt": { "useMaxWidth": true, "barHeight": 20, "topAxis": false }
}
```

`flowchart.curve` accepts `basis` (soft), `linear` (straight — best for print and
high-contrast), `natural`, `step`, `monotoneX`, `cardinal`.

`useMaxWidth: true` makes the SVG responsive to its container. Set it `false`
when exporting to PNG at a fixed size.

`htmlLabels: false` renders labels as SVG `<text>` rather than embedded HTML.
Slightly less flexible, but it makes the SVG genuinely standalone — worth it when
the output gets embedded somewhere you do not control.

## Verify, do not assume

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_contrast.py" <config.json>
```

Checks sixteen foreground/background pairs against WCAG AA (4.5:1 text, 3:1
non-text). All five bundled presets pass; brand palettes frequently do not.
