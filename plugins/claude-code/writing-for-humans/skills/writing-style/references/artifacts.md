# Workflow Artifacts

Durable Markdown a workflow produces for a person: design notes, investigation write-ups, decision records. The output style already sets the opening, the cold-read rules and where evidence goes. This adds what's specific to documents.

1. **Structure for scanning.** Use a table for anything with a repeating shape, one idea per bullet, and short sections under headings that say what they contain. There's no line limit; keep the context a reader needs to understand, evaluate or act on the document.
2. **Use visuals where structure exists.** A diagram beats a table when the shape is a flow, sequence or graph. Node labels are prose: label a step with what it does ("Group pictures by collection, then arrange each group"), not with a symbol (`GalleryPreview.arrangeTiles`), and put the symbol underneath. The exception is where the identifier is the subject, such as table names in an entity-relationship diagram.
3. **Choose the evidence format for the destination.** Short evidence stays nearby. Lengthy optional proof (logs, verification traces, long quotations) goes in a plain Markdown section, appendix or link, which is the default for ordinary documents and unknown renderers. GitHub comments and PR descriptions may use `<details>`; elsewhere use a documented native collapsible block only when it's supported. Don't invent syntax or assume raw HTML works, and never fold away what a reader needs to assess a claim or make a decision.
4. **Asks follow `questions.md`.** Anything asking for a decision may also use the optional check in `cold-reader.md`.
