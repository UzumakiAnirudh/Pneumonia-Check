# Chapter 5 — JavaScript & TypeScript from zero

[← Chapter 4](04-html-css-basics.md) · [README](../../README.md) · Next: [Chapter 6 →](06-react-basics.md)

JavaScript (JS) makes web pages do things. TypeScript (TS) is JavaScript with **types** that catch
mistakes before the code runs. PneumoScan's website is written in TypeScript.

**Where to try code:**

- In the browser: press `F12` → **Console** tab → type and press `Enter`.
- With Node.js: create `test.js`, run `node test.js` in a terminal.

---

## 5.1 Values and variables

```js
const threshold = 0.75; // const: cannot be reassigned (use by default)
let attempts = 0; // let: can change
attempts = attempts + 1; // or attempts += 1, or attempts++

// The basic types
const n = 42; // number (whole or decimal)
const s = "PNEUMONIA"; // string — "double", 'single' or `backtick` quotes
const ok = true; // boolean
let nothing = null; // intentionally empty
let notSet; // undefined — no value yet

console.log(s, n); // prints: PNEUMONIA 42
console.log(typeof n); // "number"
```

Lines ending with `;` are statements; `//` starts a comment; `/* ... */` comments several lines.

## 5.2 Operators

```js
1 + 2;
5 - 3;
2 * 3;
7 / 2; // 3, 2, 6, 3.5
7 % 2; // 1 (remainder)
2 ** 3; // 8 (power)
"Pneu" + "monia"; // "Pneumonia" (string joining)

5 === 5;
5 !== 4; // strict equality — ALWAYS use === and !==
5 == "5"; // true (!) loose equality converts types — avoid
a > b;
a <= b;
true && false;
true || false;
!true; // and, or, not
const value = maybe ?? 0; // use 0 if maybe is null/undefined
const name = user?.name; // undefined instead of an error if user is missing
```

## 5.3 Strings

```js
const label = "Pneumonia";
label.length; // 9
label.toUpperCase(); // "PNEUMONIA"
label.includes("monia"); // true
label.slice(0, 4); // "Pneu"
`Confidence: ${(0.973 * 100).toFixed(1)}%`; // "Confidence: 97.3%" — template string
```

## 5.4 Decisions and loops

```js
if (confidence >= threshold) {
  console.log("High confidence");
} else if (confidence >= 0.5) {
  console.log("Borderline");
} else {
  console.log("Low confidence");
}

const level = confidence >= threshold ? "high" : "low"; // ternary: condition ? a : b

for (let i = 0; i < 3; i++) console.log(i); // 0 1 2
for (const label of ["NORMAL", "VIRAL"]) console.log(label);
let k = 0;
while (k < 3) k++;
```

## 5.5 Functions

```js
function pct(value, digits = 1) {
  // digits has a default value
  return `${(value * 100).toFixed(digits)}%`;
}
pct(0.973); // "97.3%"

const double = (x) => x * 2; // arrow function (short form)
const add = (a, b) => {
  // arrow function with a body
  const sum = a + b;
  return sum;
};
```

Functions are values: they can be stored in variables and passed to other functions (as in `map` below).

## 5.6 Arrays

```js
const probs = [0.1, 0.7, 0.2];
probs[0]; // 0.1 (first item — counting starts at 0)
probs.length; // 3
probs.push(0.5); // add to the end

probs.map((p) => p * 100); // [10, 70, 20, 50] — transform each
probs.filter((p) => p > 0.15); // [0.7, 0.2, 0.5] — keep some
probs.find((p) => p > 0.5); // 0.7 — first match
probs.reduce((sum, p) => sum + p, 0); // 1.5 — combine into one
Math.max(...probs); // 0.7 — "..." spreads the array into arguments
[...probs].sort((a, b) => b - a); // copy, then sort descending
```

## 5.7 Objects

```js
const result = {
  model: "densenet",
  stage1: { label: "PNEUMONIA", confidence: 0.973 },
};
result.model; // "densenet"
result.stage1.confidence; // 0.973
result["model"]; // same as result.model

const { model, stage1 } = result; // destructuring: pull out properties
const copy = { ...result, model: "swin" }; // spread: copy and change one field

Object.keys(result); // ["model", "stage1"]
Object.entries({ NORMAL: 0.1, VIRAL: 0.9 }); // [["NORMAL", 0.1], ["VIRAL", 0.9]]
```

**JSON** is the text form of objects, used to talk to the server:

```js
const text = JSON.stringify(result); // object → text
const back = JSON.parse(text); // text → object
```

## 5.8 The DOM — changing the page

The browser turns HTML into a tree of objects, the **DOM**. JavaScript can read and change it. Add this
to your `index.html` from Chapter 4:

```html
<body>
  <p id="count">Clicked 0 times</p>
  <button id="btn">Click me</button>
  <button id="theme">Toggle dark mode</button>

  <script>
    let clicks = 0;
    const btn = document.querySelector("#btn"); // find an element (CSS selector)
    const out = document.querySelector("#count");
    btn.addEventListener("click", () => {
      // run a function on every click
      clicks++;
      out.textContent = `Clicked ${clicks} times`; // change the text
    });
    document.querySelector("#theme").addEventListener("click", () => {
      document.documentElement.classList.toggle("dark"); // add/remove class="dark" on <html>
    });
  </script>
</body>
```

Other useful DOM operations: `document.createElement("li")`, `parent.appendChild(child)`,
`el.classList.add("active")`, `el.style.width = "50%"`, `input.value`.

**Events** you will meet: `click`, `input`/`change` (form fields), `submit` (forms), `keydown`,
`wheel` (mouse wheel — used by the X-ray zoom), `pointerdown`/`pointermove` (dragging).

React (Chapter 6) does these DOM updates for you automatically — but this is what happens underneath.

## 5.9 Asynchronous code: Promises, async/await, fetch

Talking to a server takes time. JavaScript doesn't stop and wait — it continues and gets the answer later
through a **Promise**. `async`/`await` lets you write this as if it were step by step:

```js
async function checkServer() {
  try {
    const res = await fetch("http://localhost:8000/api/health"); // send a GET request
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json(); // parse the JSON body
    console.log("Server status:", data.status);
  } catch (err) {
    console.error("Could not reach the server:", err.message); // network error, etc.
  }
}
checkServer();
```

Sending a file (exactly what PneumoScan's Analyze button does):

```js
async function predict(file) {
  const form = new FormData();
  form.append("file", file); // the X-ray
  form.append("model", "densenet");
  const res = await fetch("/api/predict", {
    method: "POST",
    body: form,
    credentials: "include",
  });
  return res.json();
}
```

`credentials: "include"` sends the login cookie.

## 5.10 Modules, npm and package.json

Real projects split code into files (**modules**):

```js
// format.js
export const pct = (v) => `${(v * 100).toFixed(1)}%`;

// app.js
import { pct } from "./format.js";
```

**npm** downloads libraries listed in `package.json`:

```bash
npm init -y              # create a package.json
npm install clsx         # add a library (stored in node_modules/)
npm install              # install everything listed in package.json
npm run dev              # run a script defined in package.json "scripts"
```

Never edit `node_modules/` and never commit it — anyone can recreate it with `npm install`
(`package-lock.json` pins exact versions so everyone gets the same).

## 5.11 TypeScript — JavaScript with types

Why? In JavaScript, `result.stage1.confidnce` (typo) silently gives `undefined`. TypeScript tells you
_before running_: "Property 'confidnce' does not exist".

```ts
let threshold: number = 0.75;
const labels: string[] = ["NORMAL", "BACTERIAL", "VIRAL"];

function pct(value: number, digits = 1): string {
  return `${(value * 100).toFixed(digits)}%`;
}

// Describe the shape of objects
interface StageResult {
  label: "NORMAL" | "PNEUMONIA"; // a "union": only these two strings are allowed
  confidence: number;
  temperature?: number; // ? = optional
}

type ModelChoice = "densenet" | "swin" | "both";

const r: StageResult = { label: "PNEUMONIA", confidence: 0.97 };

// Generics: a type with a parameter
const counts: Record<string, number> = { NORMAL: 227, VIRAL: 225 };
function first<T>(items: T[]): T | undefined {
  return items[0];
}

// Narrowing: TypeScript understands checks
function show(x: number | null) {
  if (x === null) return "n/a";
  return x.toFixed(2); // here TS knows x is a number
}
```

Try it: `npm install -D typescript`, write `test.ts`, run `npx tsc test.ts` → produces `test.js`, then
`node test.js`. In PneumoScan, **Vite** compiles TypeScript automatically and `npm run typecheck` checks
the whole project. All the API shapes are typed in `frontend/src/api/types.ts`.

`.tsx` files are TypeScript that also contains React's HTML-like syntax (next chapter).

## 5.12 Exercises

1. Write `reliability(confidence, threshold)` that returns `"high"` or `"low"`; test it in the console.
2. Given `const probs = { NORMAL: 0.1, BACTERIAL: 0.6, VIRAL: 0.3 }`, find the label with the highest
   probability using `Object.entries` and `reduce`.
3. With the PneumoScan backend running, write a page with a button that calls `/api/health` and shows
   the status. (Open your page from the backend's origin or use the full URL; browsers block some
   cross-origin requests — Chapter 9 explains CORS.)
4. Convert exercises 1–2 to TypeScript with an `interface` for the probabilities.

---

Next: **Chapter 6 — React from zero (and a mini X-ray app)** → [06-react-basics.md](06-react-basics.md)
