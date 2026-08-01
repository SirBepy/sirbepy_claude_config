---
name: meta-tags
description: Triggers on /meta-tags only.
---

# /meta-tags

> Ensure index.html has all required meta tags.

## Workflow

### Step 0 - Check if already done

If the user passed `skipVerification`, skip this step entirely and proceed to Step 1.

Read `index.html` and check if all 6 required meta tags already exist (description, og:title, og:description, og:image, og:url, twitter:card). If all present, print:

```
/meta-tags - already complete, skipping.
```

And stop.

### Step 1 - Gather context

Check for the following:

- `.portfolio-data/metadata.json` - for title, shortDescription, mainImage
- `assets/images/favicon.png` - for og:image fallback
- `git remote get-url origin` - to derive the GitHub Pages base URL (`https://{username}.github.io/{repo}/`), used for both og:url and og:image
- Existing meta tags in `index.html` - do not duplicate anything already there

### Step 2 - Add missing tags

Open `index.html` and check for each of these. Add only the ones that are missing:

```html
<meta name="description" content="..." />
<meta property="og:title" content="..." />
<meta property="og:description" content="..." />
<meta property="og:image" content="https://username.github.io/repo/assets/images/favicon.png" />
<meta property="og:url" content="https://username.github.io/repo/" />
<meta name="twitter:card" content="summary" />
```

Place all meta tags inside `<head>`, grouped together after any existing meta tags.

### Content rules

- `description` and `og:description` - use shortDescription from metadata.json if it exists, otherwise infer from the project
- `og:title` - use title from metadata.json if it exists, otherwise use the page title tag
- `og:image` - absolute URL built from the same Pages base as og:url (mainImage from metadata.json if it exists, otherwise `assets/images/favicon.png`), e.g. `https://username.github.io/repo/assets/images/favicon.png`. If the Pages base can't be derived (no git remote), omit the og:image tag entirely rather than emit a relative URL.

### Step 3 - Verify absolute URLs

Re-read the written `<head>`. Confirm `og:image` (if present) and `og:url` both start with `https://`. If og:image was omitted per the fallback above, note that in the Step 4 summary rather than treating it as a failure.

### Step 4 - Confirm

Tell the user which tags were added and which were already present.
Do not commit - the user handles that.
