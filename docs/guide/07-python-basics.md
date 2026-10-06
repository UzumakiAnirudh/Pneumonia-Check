# Chapter 7 — Python from zero

[← Chapter 6](06-react-basics.md) · [README](../../README.md) · Next: [Chapter 8 →](08-fastapi-basics.md)

Python runs PneumoScan's server and all the AI code. It is famous for being readable — many lines read
almost like English.

**Where to try code:**

- Interactive: type `python3` (Windows: `python`) in a terminal; you get a `>>>` prompt. Type code and
  press `Enter`. Leave with `exit()`.
- Scripts: save code in `hello.py`, run `python3 hello.py`.
- VS Code: open a `.py` file and press the ▶ button (top right) after installing the Python extension.

---

## 7.1 First program

```python
print("Hello, PneumoScan!")      # print shows text
name = input("Your name? ")      # input asks the user (in scripts)
print("Hello,", name)
```

`#` starts a comment. **Indentation (4 spaces) is part of the language** — it shows which lines belong
to an `if`, a loop or a function.

## 7.2 Numbers, strings, booleans

```python
age = 4                 # int
confidence = 0.973      # float
label = "PNEUMONIA"     # str
is_valid = True         # bool (True / False)
nothing = None          # no value

7 / 2      # 3.5   (division)
7 // 2     # 3     (whole-number division)
7 % 2      # 1     (remainder)
2 ** 10    # 1024  (power)
round(0.97345, 3)   # 0.973

type(label)          # <class 'str'>
int("42"), float("0.5"), str(3)   # converting between types
```

Strings:

```python
s = "Pneumonia"
len(s)                       # 9
s.upper(), s.lower()         # 'PNEUMONIA', 'pneumonia'
s[0], s[-1], s[0:4]          # 'P', 'a', 'Pneu'   (indexing and slicing)
"monia" in s                 # True
"a,b,c".split(",")           # ['a', 'b', 'c']
" - ".join(["NORMAL", "VIRAL"])   # 'NORMAL - VIRAL'
f"{confidence:.1%}"          # '97.3%'   ← f-string with formatting
f"{1234567:,}"               # '1,234,567'
```

## 7.3 Collections

```python
# list — ordered, changeable
labels = ["NORMAL", "BACTERIAL"]
labels.append("VIRAL")
labels[1]                    # 'BACTERIAL'
labels[-1]                   # 'VIRAL' (last)
len(labels)                  # 3

# tuple — ordered, fixed
size = (224, 224)
width, height = size         # unpacking

# dict — key → value
probs = {"NORMAL": 0.1, "PNEUMONIA": 0.9}
probs["PNEUMONIA"]           # 0.9
probs.get("VIRAL", 0.0)      # 0.0 (default when missing)
probs["VIRAL"] = 0.0         # add
for key, value in probs.items():
    print(key, value)

# set — unique items
{"NORMAL", "NORMAL", "VIRAL"}    # {'NORMAL', 'VIRAL'}
```

## 7.4 Decisions

```python
if confidence >= 0.75:
    level = "high"
elif confidence >= 0.5:
    level = "borderline"
else:
    level = "low"

level = "high" if confidence >= 0.75 else "low"     # one-line form
# comparisons: ==  !=  <  <=  >  >=     logic: and  or  not
```

## 7.5 Loops

```python
for label in ["NORMAL", "BACTERIAL", "VIRAL"]:
    print(label)

for i in range(3):            # 0, 1, 2
    print(i)

for i, label in enumerate(labels):     # index and value
    print(i, label)

for name, p in zip(["NORMAL", "PNEUMONIA"], [0.1, 0.9]):   # walk two lists together
    print(name, p)

count = 0
while count < 3:
    count += 1

# comprehensions — build a list/dict in one line
squares = [x * x for x in range(5)]                # [0, 1, 4, 9, 16]
high = [p for p in [0.2, 0.8, 0.9] if p > 0.5]     # [0.8, 0.9]
pct = {k: round(v * 100) for k, v in probs.items()}
```

`break` leaves a loop early; `continue` skips to the next round.

## 7.6 Functions

```python
def reliability(confidence: float, threshold: float = 0.75) -> str:
    """Return 'high' or 'low' (this text is a docstring — documentation)."""
    return "high" if confidence >= threshold else "low"

reliability(0.9)                    # 'high'
reliability(0.9, threshold=0.95)    # 'low'  (keyword argument)

def summary(*values, **options):    # any number of positional / keyword arguments
    print(values, options)
summary(1, 2, digits=3)             # (1, 2) {'digits': 3}
```

`: float` and `-> str` are **type hints** — documentation that tools check. Variables created inside a
function exist only there (**scope**).

## 7.7 Errors and exceptions

```python
try:
    value = float("abc")
except ValueError as err:
    print("Not a number:", err)
finally:
    print("This always runs")

raise ValueError("Something is wrong")      # signal an error yourself
```

Read error messages from the **bottom**: the last line says what went wrong; the lines above show where.

## 7.8 Files and paths

```python
from pathlib import Path

folder = Path("data") / "raw"            # builds 'data/raw' (works on Windows too)
folder.mkdir(parents=True, exist_ok=True)
(folder / "notes.txt").write_text("hello")
text = (folder / "notes.txt").read_text()
for p in Path("data").rglob("*.jpeg"):   # every .jpeg in all sub-folders
    print(p.name)

with open("bytes.bin", "rb") as f:       # 'rb' = read bytes (images are bytes)
    data = f.read()
```

`with` closes the file automatically, even if an error happens.

## 7.9 Modules, packages, pip and virtual environments

```python
import json                                   # standard library module
from pathlib import Path                      # import one thing
import numpy as np                            # installed library with a nickname
from app.services.preprocessing import load_image   # our own code (backend/app/services/preprocessing.py)
```

- A **module** is a `.py` file; a **package** is a folder with `__init__.py`.
- **pip** installs libraries; a **virtual environment** keeps them per project:

```bash
python3 -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install numpy
pip freeze                          # list installed packages
pip install -r requirements.txt     # install a project's list
deactivate                          # leave the environment
```

`if __name__ == "__main__":` at the bottom of a script means "run this only when the file is executed
directly, not when it is imported" — every training script uses it.

## 7.10 Classes and objects

```python
class Patient:
    hospital = "Unknown"                         # class attribute (shared)

    def __init__(self, patient_id: str, age: int):   # constructor
        self.patient_id = patient_id             # instance attributes
        self.age = age

    def is_child(self) -> bool:                  # method
        return self.age < 18

p = Patient("p_001", 4)
p.is_child()        # True

class ChildPatient(Patient):                     # inheritance: a ChildPatient *is a* Patient
    def is_child(self) -> bool:
        return True
```

**Dataclasses** — short classes that hold data (used throughout the backend):

```python
from dataclasses import dataclass

@dataclass
class StageResult:
    label: str
    confidence: float

r = StageResult("PNEUMONIA", 0.97)
print(r)            # StageResult(label='PNEUMONIA', confidence=0.97)
```

The `@` lines are **decorators** — they wrap a function or class to add behaviour (FastAPI uses
`@app.get(...)`, Chapter 8).

## 7.11 Useful standard-library modules in this project

| Module       | Used for                             | Example                                         |
| ------------ | ------------------------------------ | ----------------------------------------------- |
| `json`       | JSON files                           | `json.loads(text)`, `json.dumps(obj, indent=2)` |
| `csv`        | CSV files                            | `csv.writer(f).writerow(["path", "label"])`     |
| `pathlib`    | Paths                                | see 7.8                                         |
| `argparse`   | Command-line options for scripts     | see 7.13                                        |
| `hashlib`    | Hashes (duplicate detection, tokens) | `hashlib.md5(data).hexdigest()`                 |
| `datetime`   | Dates and times                      | `datetime.now(timezone.utc)`                    |
| `re`         | Regular expressions (text patterns)  | `re.search(r"person(\d+)_bacteria", name)`      |
| `subprocess` | Run other programs                   | `subprocess.run(["git", "clone", url])`         |

## 7.12 NumPy, OpenCV and pandas — working with images and tables

```python
import numpy as np
import cv2

img = cv2.imread("xray.jpeg", cv2.IMREAD_GRAYSCALE)   # an image is a NumPy array
img.shape            # e.g. (1858, 2090)  → height, width
img.dtype            # uint8  → whole numbers 0–255
img.min(), img.max(), img.mean()

small = cv2.resize(img, (224, 224), interpolation=cv2.INTER_AREA)
clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(small)
cv2.imwrite("small.png", clahe)

x = small.astype(np.float32) / 255.0      # convert to decimals 0–1
x[0:10, 0:10]                              # slicing: top-left 10×10 block
x * 2 + 1                                  # maths applies to every pixel at once ("vectorised")
np.stack([x, x, x])                        # (3, 224, 224) — three channels
```

```python
import pandas as pd

df = pd.read_csv("training/data/splits.csv")
df.head()                                  # first rows
df["label"].value_counts()                 # count per class
test = df[df["split"] == "test"]           # filter rows
pd.crosstab(df["split"], df["label"])      # the table printed by prepare_data.py
```

## 7.13 Exercise: write a small command-line tool

Save as `xray_info.py` and run `python3 xray_info.py path/to/xray.jpeg --size 224`:

```python
"""Print basic information about an X-ray and save a preprocessed copy."""
import argparse
from pathlib import Path

import cv2


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path, help="Path to an X-ray image")
    parser.add_argument("--size", type=int, default=224, help="Output size in pixels")
    args = parser.parse_args()

    img = cv2.imread(str(args.image), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise SystemExit(f"Could not read {args.image}")
    print(f"{args.image.name}: {img.shape[1]}×{img.shape[0]} px, mean brightness {img.mean():.1f}")

    small = cv2.resize(img, (args.size, args.size), interpolation=cv2.INTER_AREA)
    out = args.image.with_name(args.image.stem + f"_{args.size}.png")
    cv2.imwrite(str(out), small)
    print("Saved", out)


if __name__ == "__main__":
    main()
```

Every training script (`train.py`, `evaluate.py`, ...) has exactly this structure — open one and compare.

## 7.14 More exercises

1. Write `split_counts(rows)` that takes a list of `(split, label)` tuples and returns a dict of counts.
2. Read `training/data/splits.csv` with the `csv` module (not pandas) and count images per split.
3. Write a class `Thresholds` with a method `level(confidence)`; create two objects with different
   thresholds and compare their answers.
4. Load an X-ray with OpenCV, compute the mean brightness of the left and right halves, and print which is
   brighter (a mini version of the validator's symmetry check).

---

Next: **Chapter 8 — FastAPI from zero (build a small image API)** → [08-fastapi-basics.md](08-fastapi-basics.md)
