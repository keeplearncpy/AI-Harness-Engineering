# UI Interaction Document: {Feature/Page Name}

## 1. Page Layout
- **Route**: `/path`
- **Layout type**: Full-page / Modal / Sidebar

## 2. Component Tree
```
PageLayout
├── Header
│   ├── Logo
│   └── NavMenu
├── MainContent
│   ├── SearchBar
│   ├── DataTable
│   │   └── TableRow (repeated)
│   └── Pagination
└── Footer
```

## 3. Interaction States

### 3.1 Loading
- Skeleton loader or spinner while fetching data.

### 3.2 Empty
- Illustration + "No data yet" message + CTA button.

### 3.3 Error
- Toast notification with retry option.
- Inline error messages for form fields.

### 3.4 Edge Cases
- Long text truncation with tooltip.
- Responsive behavior at breakpoints.

## 4. Data Flow
1. User navigates to page → fetch API data
2. Display data in components
3. User interacts → update local state → submit to API
4. Refresh data on success

## 5. Accessibility
- All interactive elements keyboard-navigable.
- Proper ARIA labels and roles.
- Color contrast meets WCAG AA.
