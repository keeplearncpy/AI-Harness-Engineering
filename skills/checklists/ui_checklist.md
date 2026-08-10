# UI Checklist

Use this checklist to validate frontend component implementations.

## Component Structure
- [ ] Each component in its own file
- [ ] Clear prop types (TypeScript interfaces)
- [ ] Single responsibility principle
- [ ] No inline styles (use CSS modules or Tailwind)

## State Management
- [ ] Loading state handled (skeleton/spinner)
- [ ] Empty state handled (illustration + message)
- [ ] Error state handled (toast/inline message + retry)
- [ ] Edge cases handled (long text, null values, zero)

## Interactions
- [ ] All buttons/links have hover and focus states
- [ ] Form validation with clear error messages
- [ ] Confirm dialogs for destructive actions
- [ ] Optimistic updates where appropriate

## Accessibility
- [ ] Semantic HTML elements used
- [ ] ARIA labels on interactive elements
- [ ] Keyboard navigation works (Tab, Enter, Escape)
- [ ] Color contrast meets WCAG AA (4.5:1)

## Performance
- [ ] No unnecessary re-renders (React.memo, useMemo)
- [ ] Images lazy-loaded
- [ ] Debounced search inputs
- [ ] Code splitting for large pages

## Responsive
- [ ] Mobile-first design
- [ ] Tested at 320px, 768px, 1024px, 1440px
- [ ] Touch targets at least 44x44px on mobile
