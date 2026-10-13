# Dynamic Skill Discovery & Context Optimization

Avoid bloating the prompt context with full skill manuals or hundreds of static instructions. Use `skills-cli` to discover and load skills dynamically on demand.

## Guidelines

1. **Task Matching**: When faced with a specialized workflow (design, research, planning, testing, slides, UI), check for specialized skills using `skills-cli match "<task description>"`.
2. **Progressive Disclosure**: Do not read or dump entire skill files if only a specific section or procedure is needed. Inspect the outline with `skills-cli info <skill>` and load the exact section via `skills-cli load <skill> --section "<heading>"`.
3. **Context Economy**: Treat the context window as high-value memory. Load instructions for the active step, then proceed with code or artifact generation without carrying unnecessary procedural text across subsequent turns.
