# Graphify Development & Reasoning Guidelines

To prevent context drift, reduce token overhead, and maintain structural memory of the workspace, follow these Graphify guidelines:

- **Rule 1**: For any codebase-wide question, architecture search, or dependency tracing, always query the local graph map first using `graphify query "<question>"`.
- **Rule 2**: Rely on the graph's EXTRACTED and INFERRED edges to identify code paths before opening or reading files one by one. Do not scan the entire codebase blindly.
- **Rule 3**: After major updates, new feature implementations, or significant code refactors, ALWAYS run `graphify . --update` (or `graphify . --code-only`) to refresh the knowledge graph before marking the task complete.

