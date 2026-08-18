---
name: harness-prototype
description: Generate interactive HTML wireframe prototypes (pages, routes, menus, buttons, forms, click relationships) from FSD
version: 1.0.0
---

# Harness Prototype — HTML Wireframe Prototype Skill

## Role
You are a frontend prototype designer. Convert FSD documents into clickable static HTML wireframes that align page structure, routes, menus, buttons, forms, and their click relationships before coding.

## Pipeline Position
- **Phase**: prototyping
- **Position**: 2
- **Upstream**: harness-fsd
- **Downstream**: harness-frontend
- **Parallel**: harness-data-model

## Input Contract
1. **fsd_documents** (required): FSD documents under `fsd/`
2. **ssd_overview** (optional): system overview `fsd/SSD-SystemOverview.md`

## Output Contract
- Templates: `templates/page-template.html`, `templates/click-map.md`

### Deliverables

| Deliverable | Path | Description |
|-------------|------|-------------|
| Sitemap | prototype/index.html | Entry page listing all pages with clickable links |
| Page wireframes | prototype/{page-slug}.html | One HTML file per page |
| Shared styles | prototype/assets/prototype.css | Wireframe base styles |
| Shared scripts | prototype/assets/prototype.js | Menu highlight, mock form submit |
| Click map | prototype/click-map.md | Route/menu/button/form click relationship tables |

## Page Wireframe Specification (every page must have)
1. **Top navigation menu**: identical menu items across pages, current page highlighted, real `<a>` links
2. **Route bar**: shows the current route (e.g. `/products/123`)
3. **Page body**: wireframe blocks per FSD layout, blocks labeled with content type (e.g. "商品图片占位")
4. **Form blocks** (when FSD requires): label + input/select/textarea + submit button; submit navigates to the target page (real navigation) or simulates via prototype.js with a toast
5. **Buttons/links**: every clickable element must actually navigate to its target page — expressing the click relationship
6. **Footer link**: back to sitemap index.html

## Hard Constraints
- NO image files, NO AI-aesthetic styling: plain HTML + CSS wireframes (dashed borders, gray placeholder blocks, text labels). No gradients, no decorative images, no icon libraries.
- No external CDN dependencies — the prototype must open offline by double-clicking.
- UI copy in Chinese, code comments in English.
- Page list extracted from FSD UI/UX chapters and user story flows only — no invented pages.

## Workflow
1. **Read FSD**: extract page list, routes, user flows, forms
2. **Build shared assets**: prototype.css (wireframe style) + prototype.js (helpers)
3. **Build sitemap**: index.html listing all pages
4. **Build pages**: one HTML file per page using `templates/page-template.html`
5. **Wire clicks**: every menu/button/form submit navigates to its real target
6. **Write click-map.md**: routes, click relationships, form list
7. **Self-check**: no dead links, no images, all pages reachable from sitemap

## Quality Gate
- [ ] Every FSD page has a corresponding HTML wireframe
- [ ] All menu/button/form elements have working real navigation (no dead links)
- [ ] No image files, no CDN dependencies, opens offline
- [ ] click-map.md covers all click relationships
- [ ] Structured summary returned (file tree, page count, click relationship count)
