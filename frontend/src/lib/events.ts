/** Window events shared across the app (dispatched with `new CustomEvent(name)`). */

/** An expense was created or changed outside the current page's own fetch (chat,
 * global modals): lists listening to it refetch. */
export const EXPENSE_CREATED_EVENT = "expense-created";
