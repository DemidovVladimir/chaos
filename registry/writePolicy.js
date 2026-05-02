// writePolicy.js — strfry write policy for the neuro-spati relay.
//
// Receives a JSON event on stdin per line and writes a single-line
// JSON response with shape:
//   {"id": "<event_id>", "action": "accept" | "reject" | "shadowReject", "msg": "<reason>"}
//
// strfry calls this for EVERY incoming event before persistence.
// Keep it fast (no network I/O) and well-bounded.

const fs   = require("fs");
const path = require("path");

const ALLOWED_KINDS = new Set([
    0,        // profile metadata
    5,        // NIP-09 deletion request
    8,        // NIP-58 badge award
    13,       // NIP-17 seal
    14,       // NIP-17 rumor (never published — but allow if seen)
    1059,     // NIP-17 gift wrap
    1985,     // NIP-32 label
    30009,    // NIP-58 badge definition
    30402,    // NIP-99 classified listing
    30403,    // NIP-99 draft
]);

// NIP-51 lists family
for (let k = 30000; k <= 30099; k++) ALLOWED_KINDS.add(k);

const PUBKEY_ALLOWLIST_FILE = "/app/strfry-db/pubkey_allowlist.txt";
const PUBKEY_BLOCKLIST_FILE = "/app/strfry-db/pubkey_blocklist.txt";

// PoW-exempt kinds: encrypted DMs (relay can't read content; sybil
// is self-limiting because recipient can ban the pubkey).
const POW_EXEMPT_KINDS = new Set([13, 14, 1059]);

// Per-pubkey rate limit.
const RATE_LIMIT_PER_MIN  = 10;
const RATE_LIMIT_PER_HOUR = 100;

// In-memory state. Reset on restart.
const recentEventsByPubkey = new Map();   // pubkey -> [timestamps]

function loadList(file) {
    try {
        const txt = fs.readFileSync(file, "utf-8");
        return new Set(
            txt.split("\n")
               .map(s => s.trim())
               .filter(s => s && !s.startsWith("#"))
        );
    } catch {
        return new Set();
    }
}

let allowlist = loadList(PUBKEY_ALLOWLIST_FILE);
let blocklist = loadList(PUBKEY_BLOCKLIST_FILE);

// Reload lists every minute so moderation actions take effect without
// restarting strfry.
setInterval(() => {
    allowlist = loadList(PUBKEY_ALLOWLIST_FILE);
    blocklist = loadList(PUBKEY_BLOCKLIST_FILE);
}, 60_000);

function leadingZeroBits(hex) {
    let bits = 0;
    for (const ch of hex) {
        const n = parseInt(ch, 16);
        if (n === 0) { bits += 4; continue; }
        if (n < 2)  return bits + 3;
        if (n < 4)  return bits + 2;
        if (n < 8)  return bits + 1;
        return bits;
    }
    return bits;
}

function checkRateLimit(pubkey, now) {
    const arr = recentEventsByPubkey.get(pubkey) || [];
    const minAgo  = now - 60_000;
    const hourAgo = now - 3_600_000;
    const trimmed = arr.filter(t => t > hourAgo);
    const inMin   = trimmed.filter(t => t > minAgo).length;
    const inHour  = trimmed.length;
    if (inMin >= RATE_LIMIT_PER_MIN)  return "rate_limit_per_min";
    if (inHour >= RATE_LIMIT_PER_HOUR) return "rate_limit_per_hour";
    trimmed.push(now);
    recentEventsByPubkey.set(pubkey, trimmed);
    return null;
}

function decide(req) {
    const ev = req.event;
    if (!ev || typeof ev !== "object") {
        return { action: "reject", msg: "malformed event" };
    }

    // 1. Kind allowlist
    if (!ALLOWED_KINDS.has(ev.kind)) {
        return { action: "reject", msg: `kind ${ev.kind} not supported by this relay` };
    }

    // 2. Pubkey blocklist (silent shadow-reject — accept on the wire,
    // never index)
    if (blocklist.has(ev.pubkey)) {
        return { action: "shadowReject", msg: "pubkey blocked" };
    }

    // 3. Pubkey allowlist (only enforced if non-empty — invite-only mode)
    if (allowlist.size > 0 && !allowlist.has(ev.pubkey)) {
        return { action: "reject", msg: "pubkey not on invite allowlist" };
    }

    // 4. PoW for non-DM kinds. strfry's minPowDifficulty already
    // enforces this globally; we duplicate the check so we can exempt
    // DM kinds explicitly.
    if (!POW_EXEMPT_KINDS.has(ev.kind)) {
        const pow = leadingZeroBits(ev.id);
        if (pow < 20) {
            return { action: "reject", msg: `pow ${pow} below minimum 20` };
        }
    }

    // 5. Rate limit
    const now = Date.now();
    const rateMsg = checkRateLimit(ev.pubkey, now);
    if (rateMsg) {
        return { action: "reject", msg: rateMsg };
    }

    return { action: "accept" };
}

// strfry plugin protocol — read NDJSON on stdin, write NDJSON on stdout.
const rl = require("readline").createInterface({ input: process.stdin });
rl.on("line", (line) => {
    let req;
    try {
        req = JSON.parse(line);
    } catch {
        return;
    }
    const verdict = decide(req);
    const out = { id: req.event && req.event.id, action: verdict.action, msg: verdict.msg || "" };
    process.stdout.write(JSON.stringify(out) + "\n");
});
