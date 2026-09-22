# Writing examples

All scenarios, facts and wording below were independently invented for this plugin. They do not reproduce or anonymize personal conversations, workplace events or archived output. Examples describe clarity failures, not a mandatory voice or output template.

## Explain shorthand

Context: a fictional public seed catalog lets readers filter by planting month. The filter changes the displayed cards but the download still contains every month.

Before: “Month narrowing is display-local; export retains the full selection domain.”

After: “The month filter changes the cards on screen, but the download still includes seeds for every month.”

What improved: the reader can explain the difference between what they see and what they download. “Filter” remains useful vocabulary; invented terminology disappears.

## State the requirement before referencing it

Context: a fictional puzzle app must save an unfinished puzzle when the browser closes. The product requirement is named PZ-7.

Before: “This violates PZ-7.”

After: “Closing the browser loses the unfinished puzzle. The requirement says players should be able to return to their saved progress (PZ-7).”

What improved: the reader understands the failure without opening the requirement. The reference remains available for verification.

## Explain consequences in a question

Context: a fictional community telescope booking system allows cancellations. Reopening a canceled slot lets someone else book it; holding it prevents a replacement booking. The policy is undecided.

Before: “Should canceled slots reopen?”

After: “When someone cancels a telescope booking, should the slot become available to another person? Reopening it lets someone else use the time; keeping it reserved prevents a replacement booking.”

What improved: the question makes both outcomes explicit without inventing a policy or disguising the choice as a technical requirement.

## Let evidence support an intelligible claim

Context: a fictional board-game inventory marks unavailable games as reservable because its availability check ignores the repair flag. The synthetic evidence location is inventory.ts:48.

Before: “inventory.ts:48 bypasses repair status on the reservation predicate.”

After: “Games undergoing repair can still be reserved because the availability check ignores their repair status (inventory.ts:48).”

What improved: the reader understands the behavior and reason before consulting the evidence. An anchored comment may use the visible symbol name where that is clearer.

## Keep enough context without repeating it

Established exchange: “The printable walking-map legend uses symbols that disappear in grayscale. Please add text labels.” Work performed: labels were added; a grayscale print preview was checked.

Overwritten update: “The walking map has a legend. A legend explains the map symbols. Some people print maps without color. I changed the legend so the map can be read without color.”

Better update: “Added text labels to the legend and checked the grayscale print preview. Each symbol is now identifiable without color.”

What improved: the update retains the outcome and verification while using context already present in the exchange. A standalone release note would name the walking map.

## Preserve uncertainty

Context: in a fictional aquarium exhibit schedule, a display sometimes repeats yesterday’s feeding time. A cached response is one possible cause; it has not been verified.

Before: “A cached response may be causing the display to repeat yesterday’s feeding time.”

Bad rewrite: “The cache causes the incorrect feeding time.”

Correct action: retain the original sentence or make an equally qualified revision.

What matters: a more decisive tone cannot turn a hypothesis into an established cause.

## Leave good writing alone

Context: a fictional origami guide adds a diagram showing which side of the paper faces upward at the first fold.

Draft: “The first-fold diagram now labels the side that should face upward, so readers can start without guessing.”

Correct action: keep the draft. Additional headings, a summary or a more conversational rewrite would add little value.

## Preserve machine values and clarify prose fields

Context: a fictional fountain controller emits a JSON status object. The key `state` must equal `WAITING_FOR_PRESSURE`; `retry_seconds` must remain 15. Its human-readable `message` can be edited.

Before message: “Pressure prerequisite unsatisfied; actuation deferred.”

After message: “The fountain is waiting for enough water pressure before starting.”

What matters: preserve keys, enum values, numbers and valid JSON. The explanatory message follows the same clarity standard as other prose. Do not infer a fault, a guaranteed start time or a new retry policy.

## Review questions for every example

Can a reader restate the behavior, relevant consequence and requested action where one exists? Does the revision preserve all established facts and uncertainty? Is any omitted background actually present in the supplied exchange? Does a reference support meaning rather than carry it? Would leaving an already-good draft alone be better than rewriting it?
