# Design System

## Direction

LiveScout is a focused product interface for a desktop operator searching in a dim room for several minutes at a time. The visual direction is a restrained dark interface with a warm graphite canvas, a cool blue interaction accent, and coral reserved for live status.

## Color

- **Canvas**: warm graphite near `#111214`.
- **Surface**: layered graphite surfaces for the application shell and result rows.
- **Ink**: warm off-white for primary text, muted gray for supporting text.
- **Action**: cool blue for search actions, links, focus, and selected states.
- **Live**: coral red only for active live indicators and related warnings.
- **Success**: muted green for verified state.

Keep the palette restrained. Accent colors communicate state and action rather than decoration.

## Typography

Use a familiar system sans stack with a compact product scale. Headings use strong weight and negative tracking for hierarchy; body copy stays readable and concise. Do not use display fonts for controls, labels, or result metadata.

## Layout

Use a search-first flow:

1. Brand and public-discovery status.
2. Search promise and keyword input.
3. Example queries.
4. Verified result list.
5. Freshness and source-boundary notes.

Use predictable alignment and generous vertical rhythm. Result rows should prioritize the broadcast title, source, verification time, and the external Facebook action.

## Components

Use shadcn/ui conventions with local, editable components. Keep a consistent vocabulary for buttons, inputs, badges, result rows, loading skeletons, empty states, and error states. Every interactive control needs visible hover, focus, disabled, loading, and error behavior where applicable.

## Motion

Use short, state-driven transitions only. Loading uses skeleton content; motion must respect `prefers-reduced-motion` and must never delay the search task.

## References

- **Linear**: clear hierarchy and restrained product density.
- **Raycast**: fast, search-centered interaction.
- **shadcn/ui**: editable component primitives and consistent control language.
