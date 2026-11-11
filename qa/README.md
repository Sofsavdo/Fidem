# QA harness

Runs the **real** FastAPI app on an in-memory MongoDB (mongomock) - no Atlas, no
Telegram, no AI keys - and drives it from scripts and a real mobile browser.

```bash
pip install mongomock-motor httpx uvicorn -r ../backend/requirements.txt
cd frontend && REACT_APP_BACKEND_URL=http://localhost:18100 BUILD_PATH=/tmp/qa-build npm run build
python qa/qa_server.py &              # API on :18100 (AI/Telegram stubbed, GridFS -> memory)
python qa/seed.py                     # 15 onboarded users via the real endpoints
QA_BUILD=/tmp/qa-build node qa/static.js &   # frontend on :18101
python qa/smoke.py                    # every GET endpoint: no 5xx
python qa/smoke_mut.py                # every POST/PATCH/DELETE with schema-generated bodies
python qa/flows.py && python qa/flows2.py   # auth, feed, likes/match, chat paywall, payments, privacy, IDOR
node qa/crawl.js qa@fidem.uz uz run shots   # 31 pages: console/API errors, overflow, raw i18n keys
node qa/onboard.js                    # register -> consent -> 3 steps -> feed in a browser
node qa/chatdup.js                    # sent message shows once even if the WS echo beats the HTTP reply
```
`crawl.js <user> <lang> <tag> [shots|admin]` writes screenshots to `qa/shots/`.
Needs `playwright` (`npm i playwright`) for the node scripts. Limits are unit-tested
separately, so the harness switches the rate limiters off.
