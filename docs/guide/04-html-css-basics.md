# Chapter 4 — HTML & CSS from zero

[← Chapter 3](03-how-it-works.md) · [README](../../README.md) · Next: [Chapter 5 →](05-javascript-typescript-basics.md)

Every web page — including PneumoScan's — is built from three languages:

| Language       | Role                                                 | Analogy                 |
| -------------- | ---------------------------------------------------- | ----------------------- |
| **HTML**       | _What_ is on the page (headings, images, buttons)    | The skeleton            |
| **CSS**        | _How it looks_ (colours, sizes, layout)              | The skin and clothes    |
| **JavaScript** | _What it does_ (react to clicks, talk to the server) | The muscles (Chapter 5) |

You need only a text editor (VS Code) and a browser. Nothing to install.

---

## 4.1 Your first web page (5 minutes)

1. Create a folder `web-practice` on your Desktop and open it in VS Code.
2. Create a file `index.html` and type:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>My first page</title>
  </head>
  <body>
    <h1>PneumoScan practice</h1>
    <p>This is a paragraph.</p>
  </body>
</html>
```

3. Save, then double-click `index.html` in Finder/Explorer — it opens in your browser. 🎉

What each line means:

| Line                         | Meaning                                                                               |
| ---------------------------- | ------------------------------------------------------------------------------------- |
| `<!doctype html>`            | "This is a modern HTML5 document"                                                     |
| `<html lang="en">`           | The root element; the page language is English (helps screen readers and translation) |
| `<head>`                     | Information _about_ the page — not shown directly                                     |
| `<meta charset="UTF-8">`     | Use UTF-8 so all characters (é, 你, →) display correctly                              |
| `<meta name="viewport" ...>` | Make the page fit phone screens instead of zooming out                                |
| `<title>`                    | Text on the browser tab                                                               |
| `<body>`                     | Everything visible                                                                    |

## 4.2 Elements, tags and attributes

An **element** is usually an opening tag, content, and a closing tag:

```html
<p class="note">Decision support only.</p>
<!-- ↑ tag   ↑ attribute   ↑ content        ↑ closing tag -->
```

- **Attributes** add information: `class`, `id`, `href`, `src`, `alt`, `type`...
- Some elements have no content and no closing tag: `<img>`, `<input>`, `<br>`, `<meta>`.
- `<!-- ... -->` is a **comment**, ignored by the browser.
- Elements **nest** like boxes inside boxes — always close inner ones first.

## 4.3 The elements you will use most

```html
<h1>Main title</h1>
<h2>Section</h2>
<h3>Sub-section</h3>
<!-- headings, h1–h6 -->
<p>A paragraph with <strong>bold</strong> and <em>italic</em> text.</p>
<a href="https://example.com">A link</a>
<!-- href = where it goes -->
<img src="xray.png" alt="Frontal chest X-ray" width="300" />
<!-- alt = text for blind users -->

<ul>
  <!-- unordered (bulleted) list -->
  <li>Normal</li>
  <li>Pneumonia</li>
</ul>
<ol>
  <li>Upload</li>
  <li>Analyze</li>
</ol>
<!-- ordered (numbered) list -->

<table>
  <thead>
    <tr>
      <th>Model</th>
      <th>AUC</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>DenseNet121</td>
      <td>0.996</td>
    </tr>
    <tr>
      <td>Swin-T</td>
      <td>0.999</td>
    </tr>
  </tbody>
</table>

<div>A generic block container</div>
<span>A generic inline container</span>
<button>Analyze</button>
```

**Block vs inline:** block elements (`div`, `p`, `h1`, `ul`) start on a new line and take the full width;
inline elements (`span`, `a`, `strong`, `img`) flow within text.

## 4.4 Semantic structure (meaningful tags)

Instead of `div` everywhere, use tags that _say what they are_ — better for accessibility and search
engines. PneumoScan's layout uses exactly these:

```html
<header>Logo and top bar</header>
<nav aria-label="Main">Links to pages</nav>
<main id="main">
  <section aria-label="Image viewer">...</section>
  <aside>Side information</aside>
</main>
<footer>Disclaimer</footer>
```

## 4.5 Forms — collecting input

Our login and registration pages are forms:

```html
<form>
  <label for="email">Email</label>
  <input
    id="email"
    type="email"
    autocomplete="email"
    placeholder="you@hospital.org"
    required
  />

  <label for="pw">Password</label>
  <input id="pw" type="password" minlength="8" required />

  <label><input type="checkbox" /> Save history</label>

  <label for="model">Model</label>
  <select id="model">
    <option value="densenet">DenseNet121</option>
    <option value="swin">Swin Transformer</option>
  </select>

  <input type="file" accept=".png,.jpg,.jpeg,.dcm" />
  <input type="range" min="0" max="1" step="0.05" />
  <!-- a slider -->
  <button type="submit">Create account</button>
</form>
```

- `<label for="email">` connects the text to the input with `id="email"` — clicking the label focuses
  the field and screen readers announce it. **Always label inputs.**
- `type` changes the control: `email`, `password`, `checkbox`, `radio`, `file`, `range`, `number`...
- `required`, `minlength` give basic browser validation (we also validate in JavaScript and on the server).

## 4.6 Accessibility essentials

- Every image needs `alt` text (or `alt=""` if purely decorative).
- Every input needs a label.
- Use real `<button>`s for actions — they work with the keyboard (`Tab`, `Enter`, `Space`).
- Never convey meaning by colour alone — PneumoScan always pairs colour with text and an icon.
- `aria-label`, `role="status"`, `aria-live` give extra information to screen readers.

## 4.7 CSS — making it look good

Add a `<style>` block inside `<head>` (or a separate `style.css` linked with
`<link rel="stylesheet" href="style.css">`):

```html
<style>
  body {
    font-family: system-ui, sans-serif; /* font */
    background: #f5f8fb; /* page background (PneumoScan's) */
    color: #1a2333; /* text colour */
    margin: 0;
  }
  h1 {
    color: #1e5aa8;
  } /* clinical blue */
  .card {
    /* .card = every element with class="card" */
    background: white;
    border: 1px solid #dde4ed;
    border-radius: 16px; /* rounded corners */
    padding: 20px; /* space inside */
    margin: 16px; /* space outside */
    box-shadow: 0 4px 16px rgb(16 24 40 / 0.06);
  }
  #result {
    font-weight: 700;
  } /* #result = the element with id="result" */
  button:hover {
    opacity: 0.9;
  } /* :hover = while the mouse is over it */
</style>
```

### Selectors

| Selector                      | Matches                           |
| ----------------------------- | --------------------------------- |
| `p`                           | every `<p>`                       |
| `.card`                       | every element with `class="card"` |
| `#result`                     | the element with `id="result"`    |
| `.card p`                     | `<p>` elements _inside_ a `.card` |
| `button:hover`, `input:focus` | states                            |
| `a, button`                   | both                              |

### The box model

Every element is a box: **content** → **padding** (inside space) → **border** → **margin** (outside space).
`box-sizing: border-box` makes `width` include padding and border — easier to reason about (Tailwind
sets this for you).

### Units

`px` (pixels), `rem` (relative to the root font size — `1rem` = 16 px usually), `%` (of the parent),
`vh`/`vw` (percent of the window height/width).

### Colours

`#1e5aa8` (hex), `rgb(30 90 168)`, `rgb(30 90 168 / 0.5)` (50% transparent).

## 4.8 Layout: Flexbox and Grid

**Flexbox** — arrange items in a row or column:

```css
.toolbar {
  display: flex;
  gap: 8px;
  align-items: center;
  justify-content: space-between;
}
```

**Grid** — two-dimensional layouts, e.g. the Analyze page (big viewer + side panel):

```css
.workspace {
  display: grid;
  grid-template-columns: 1.45fr 1fr;
  gap: 24px;
}
```

**Responsive design** — change the layout on small screens with a **media query**:

```css
@media (max-width: 1024px) {
  .workspace {
    grid-template-columns: 1fr;
  } /* stack on tablets/phones */
}
```

**Positioning** — `position: relative` on a parent and `position: absolute` on a child lets you stack
layers. That is how the heatmap sits exactly on top of the X-ray in the viewer.

## 4.9 CSS variables and dark mode

```css
:root {
  --bg: #f5f8fb;
  --text: #1a2333;
}
.dark {
  --bg: #090e18;
  --text: #e4eaf2;
}
body {
  background: var(--bg);
  color: var(--text);
}
```

Add `class="dark"` to `<html>` and every colour switches. PneumoScan does exactly this in
`frontend/src/styles/index.css` (colours are stored as RGB channel numbers so transparency can be added).

## 4.10 Tailwind CSS — CSS through class names

Writing CSS files for every component gets slow. **Tailwind** provides tiny ready-made classes:

| Tailwind class            | Same as CSS                                                         |
| ------------------------- | ------------------------------------------------------------------- |
| `p-4`                     | `padding: 1rem`                                                     |
| `px-3 py-2`               | horizontal / vertical padding                                       |
| `mt-6`                    | `margin-top: 1.5rem`                                                |
| `rounded-xl`              | `border-radius: 0.75rem`                                            |
| `text-sm font-semibold`   | small, semi-bold text                                               |
| `bg-primary text-white`   | our blue background, white text (colours from `tailwind.config.ts`) |
| `flex items-center gap-2` | flexbox, vertically centred, 0.5rem gaps                            |
| `grid lg:grid-cols-2`     | grid; 2 columns on large screens only                               |
| `hover:bg-surface-2`      | background change on hover                                          |
| `dark:...`                | styles applied in dark mode                                         |
| `hidden lg:flex`          | hidden on small screens, flex on large                              |

A PneumoScan button, for example:

```html
<button
  class="inline-flex h-10 items-center gap-2 rounded-xl bg-primary px-4 font-medium text-white hover:bg-primary/90"
>
  Analyze
</button>
```

## 4.11 Your browser's developer tools

Right-click anything on a page → **Inspect** (or press `F12`). You can see the HTML, the CSS applied to
each element, edit them live, and see the box model. Try it on PneumoScan: inspect the _Analyze_ button
and change its colour.

## 4.12 Exercises

1. Build a "result card" page: an `<h2>` "PNEUMONIA" in red, a paragraph "Calibrated confidence 97.3%",
   and a bar made of two `<div>`s (outer grey, inner red with `width: 97.3%`).
2. Make it a two-column grid with an `<img>` on the left; stack the columns on narrow screens.
3. Add a dark-mode class with CSS variables and a button (next chapter: make the button toggle it).
4. Rewrite exercise 1 with Tailwind classes using the CDN for quick experiments:
   `<script src="https://cdn.tailwindcss.com"></script>` in `<head>`.

---

Next: **Chapter 5 — JavaScript & TypeScript from zero** → [05-javascript-typescript-basics.md](05-javascript-typescript-basics.md)
