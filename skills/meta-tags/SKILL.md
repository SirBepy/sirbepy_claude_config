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
- `git remote get-url origin` - to construct the live URL for og:url
- Existing meta tags in `index.html` - do not duplicate anything already there

### Step 2 - Add missing tags

Open `index.html` and check for each of these. Add only the ones that are missing:

```html
<meta name="description" content="..." />
<meta property="og:title" content="..." />
<meta property="og:description" content="..." />
<meta property="og:image" content="assets/images/favicon.png" />
<meta property="og:url" content="https://username.github.io/repo/" />
<meta name="twitter:card" content="summary" />
```

Place all meta tags inside `<head>`, grouped together after any existing meta tags.

### Content rules

- `description` and `og:description` - use shortDescription from metadata.json if it exists, otherwise infer from the project
- `og:title` - use title from metadata.json if it exists, otherwise use the page title tag
- `og:image` - use mainImage from metadata.json if it exists, otherwise fall back to `assets/images/favicon.png`
- `og:url` - construct from git remote, fall back to placeholder if remote not set

### Step 3 - Confirm

Tell the user which tags were added and which were already present.
Do not commit - the user handles that.
