# Chapter 9 — The web, APIs, databases and security

[← Chapter 8](08-fastapi-basics.md) · [README](../../README.md) · Next: [Chapter 10 →](10-deep-learning-fundamentals.md)

Chapters 4–8 taught the languages. This chapter explains the **plumbing** that connects them: how a
browser reaches a server, how they exchange data, where data is stored, and how it is kept safe.

---

## 9.1 What happens when you open a website

Take `https://pneumonia-verify.vercel.app/analyze`:

| Part                          | Name              | Meaning                                           |
| ----------------------------- | ----------------- | ------------------------------------------------- |
| `https`                       | **scheme**        | Use HTTP over an encrypted connection (TLS)       |
| `pneumonia-verify.vercel.app` | **host / domain** | Which computer to talk to                         |
| `/analyze`                    | **path**          | Which page or resource on it                      |
| `?model=swin` (optional)      | **query string**  | Extra parameters                                  |
| `#results` (optional)         | **fragment**      | A position in the page (never sent to the server) |

1. **DNS** (the internet's phone book) turns the domain into an **IP address**, e.g. `76.76.21.21`.
2. The browser opens a connection to that address on **port 443** (HTTPS) — or 80 (HTTP), or a custom one
   such as `localhost:8000` during development.
3. **TLS** encrypts the connection and proves the server's identity with a **certificate** — the padlock in
   the address bar. Vercel and Render provide certificates automatically.
4. The browser sends an **HTTP request**; the server sends back an **HTTP response**.

## 9.2 HTTP in detail

A real request PneumoScan makes when you press Analyze (simplified):

```http
POST /api/predict HTTP/1.1
Host: pneumonia-verify.vercel.app
Cookie: pneumoscan_session=Kc3x...
Content-Type: multipart/form-data; boundary=----X

------X
Content-Disposition: form-data; name="model"

densenet
------X
Content-Disposition: form-data; name="file"; filename="xray.jpeg"
Content-Type: image/jpeg

<binary image bytes>
------X--
```

And the response:

```http
HTTP/1.1 200 OK
Content-Type: application/json

{"id": "e3f…", "results": [{"model": "densenet", "final_label": "NORMAL", ...}], ...}
```

**Methods:** `GET` (read, no body), `POST` (create/submit), `PUT`/`PATCH` (update), `DELETE` (remove).
**Headers** carry metadata: `Content-Type` (what the body is), `Cookie`/`Set-Cookie`, `Authorization`,
`Cache-Control`. **Status codes:**

| Range | Meaning              | Examples here                                                                                                                                                   |
| ----- | -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2xx   | Success              | 200 OK, 201 Created (registered), 204 No Content (logout)                                                                                                       |
| 3xx   | Redirect             | 301/302                                                                                                                                                         |
| 4xx   | _You_ made a mistake | 400 bad image, 401 not logged in, 404 not found, 405 method not allowed, 409 email taken, 413 too large, 422 invalid data / not an X-ray, 429 too many attempts |
| 5xx   | _The server_ failed  | 500 bug, 502/503 backend unreachable or models missing                                                                                                          |

See it yourself: open PneumoScan, press `F12` → **Network** tab → analyze an image → click the
`predict` request to see its headers, payload and response.

## 9.3 APIs and REST

An **API** is a contract: "send _this_ to _that_ address and you get _this_ back". PneumoScan's API
follows **REST** conventions — URLs name _things_, methods say what to do with them:

| Request                    | Meaning               |
| -------------------------- | --------------------- |
| `GET /api/history`         | list my analyses      |
| `GET /api/history/{id}`    | one analysis          |
| `DELETE /api/history/{id}` | delete it             |
| `DELETE /api/history`      | delete all of mine    |
| `POST /api/predict`        | create a new analysis |

**JSON** is the data format both sides speak (Chapter 5.7). Its types: object `{}`, array `[]`, string
`"..."`, number, `true`/`false`, `null`. Binary data such as images is embedded as **Base64 text** in
**data URIs** (`data:image/png;base64,iVBORw0...`) — that is how heatmaps travel to the browser.

**Same origin and CORS:** browsers only let a page call APIs on the **same origin** (scheme + host +
port) unless the API explicitly allows others via **CORS** headers. PneumoScan avoids CORS problems
entirely by putting the API _behind the same address_ as the website: Vite's proxy in development,
Vercel's rewrite in production, nginx in Docker.

## 9.4 Cookies and sessions

- A **cookie** is a small piece of text a server asks the browser to store (`Set-Cookie`) and send back on
  every later request to the same site (`Cookie`).
- PneumoScan stores only a random **session token** in it. The server keeps a _hash_ of the token mapped to
  the user, with an expiry date (7 days).
- Flags: `HttpOnly` (JavaScript cannot read it), `Secure` (HTTPS only), `SameSite=Lax` (not sent with
  cross-site form posts), `Max-Age` (expiry), `Path=/`.

## 9.5 Databases hands-on

A **database** keeps data safely between restarts and answers questions about it. Relational databases
store **tables** (rows and columns) and are queried with **SQL**.

Try it — Python includes SQLite. In a terminal: `python3`, then:

```python
import sqlite3
db = sqlite3.connect("practice.db")            # creates the file if needed
db.execute("""CREATE TABLE IF NOT EXISTS analyses (
    id INTEGER PRIMARY KEY,                    -- unique row number
    user_id TEXT NOT NULL,
    label TEXT,
    confidence REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
db.execute("INSERT INTO analyses (user_id, label, confidence) VALUES (?, ?, ?)", ("alice", "NORMAL", 0.99))
db.execute("INSERT INTO analyses (user_id, label, confidence) VALUES (?, ?, ?)", ("bob", "VIRAL", 0.71))
db.commit()
print(db.execute("SELECT label, confidence FROM analyses WHERE user_id = ?", ("alice",)).fetchall())
db.execute("UPDATE analyses SET label = ? WHERE id = ?", ("BACTERIAL", 2))
db.execute("DELETE FROM analyses WHERE user_id = ?", ("bob",))
db.commit()
```

| SQL                                          | Does                                                        |
| -------------------------------------------- | ----------------------------------------------------------- |
| `CREATE TABLE`                               | define a table and its columns                              |
| `INSERT INTO ... VALUES`                     | add a row                                                   |
| `SELECT ... FROM ... WHERE ... ORDER BY ...` | read rows                                                   |
| `UPDATE ... SET ... WHERE`                   | change rows                                                 |
| `DELETE FROM ... WHERE`                      | remove rows                                                 |
| `PRIMARY KEY`                                | unique identifier of a row                                  |
| `INDEX`                                      | speeds up searching a column (PneumoScan indexes `user_id`) |

The `?` placeholders are important: values are passed separately from the SQL text, which prevents **SQL
injection** (a user typing SQL into a form field to break or read your database).

**SQLModel** (used by PneumoScan) lets you describe tables as Python classes and query without writing
SQL:

```python
from sqlmodel import Field, Session, SQLModel, create_engine, select

class Analysis(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(index=True)
    label: str
    confidence: float

engine = create_engine("sqlite:///practice2.db")
SQLModel.metadata.create_all(engine)
with Session(engine) as s:
    s.add(Analysis(user_id="alice", label="NORMAL", confidence=0.99))
    s.commit()
    rows = s.exec(select(Analysis).where(Analysis.user_id == "alice")).all()
```

**SQLite vs PostgreSQL:** SQLite is a single file — perfect locally. PostgreSQL is a database _server_ —
used in the cloud when data must survive restarts (Chapter 20.6). PneumoScan switches with one setting,
`DATABASE_URL`.

## 9.6 Security essentials (and how PneumoScan applies them)

| Threat             | What it is                                                        | Defence in PneumoScan                                                                                                               |
| ------------------ | ----------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| Password theft     | Stolen database reveals passwords                                 | Store only **PBKDF2-SHA256** hashes, random **salt** per user, 310,000 iterations; constant-time comparison                         |
| Session theft      | Someone copies your login token                                   | Random 256-bit token; database stores only its **hash**; `HttpOnly` cookie; logout deletes it server-side; 7-day expiry             |
| **CSRF**           | Another site makes your browser submit a request with your cookie | `SameSite=Lax` cookie                                                                                                               |
| **XSS**            | Injected script runs in your page                                 | React escapes all text by default; the session cookie is `HttpOnly` anyway                                                          |
| Brute force        | Guessing passwords repeatedly                                     | 5 failures per email → 15-minute lock; same error for unknown email and wrong password                                              |
| **IDOR**           | Changing an ID in the URL to see someone else's data              | Every history query filters by the logged-in `user_id`; foreign IDs return 404                                                      |
| SQL injection      | Malicious input in queries                                        | SQLModel / parameterised queries                                                                                                    |
| Open redirect      | Login link that sends you to a malicious site                     | `safeNext()` allows only same-site paths                                                                                            |
| Privacy leaks      | Patient identity in image metadata                                | EXIF and DICOM identifier tags removed; images processed in memory; history stores only a 192-px thumbnail                          |
| **Leaked secrets** | API keys or tokens committed to Git or pasted in chats            | Keep secrets in environment variables / `.env` (git-ignored); if a token is exposed, **revoke it immediately** and create a new one |

## 9.7 Developer tools you'll use with the web

| Tool                              | What for                                                                       |
| --------------------------------- | ------------------------------------------------------------------------------ |
| Browser DevTools (`F12`)          | Elements, Console, **Network** (every request), Application (cookies, storage) |
| `curl`                            | Send HTTP requests from a terminal: `curl http://localhost:8000/api/health`    |
| FastAPI `/docs`                   | Click-to-try every endpoint                                                    |
| `sqlite3 backend/data/history.db` | Open the local database (`.tables`, `SELECT * FROM users;`, `.quit`)           |

---

Next: **Chapter 10 — Deep learning from zero** → [10-deep-learning-fundamentals.md](10-deep-learning-fundamentals.md)
