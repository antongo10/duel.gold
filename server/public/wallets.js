/* Browser wallet discovery.

   Several wallets can be installed at once and they fight over `window.ethereum`, so the reliable way to find them is
   EIP-6963: the page asks, every wallet answers with its name, icon and its own provider object. MetaMask and Phantom
   both answer. For older builds that only set a global, `window.phantom.ethereum`, `window.ethereum` and the legacy
   `window.ethereum.providers` list are read as a fallback, de-duplicated by provider identity.

   Phantom is a Solana wallet first; this backend is EVM, so Phantom is used through its Ethereum support. */

const ICON_OK = /^data:image\/(png|svg\+xml|webp|gif|jpeg);/i; // icons arrive as data: URIs from the extension; anything else is dropped
const found = [];
const listeners = new Set();
let started = false;

const RANK = (w) => (/metamask/i.test(w.name) ? 0 : /phantom/i.test(w.name) ? 1 : 2);

function add(entry) {
  if (found.some((w) => w.provider === entry.provider)) return;
  found.push(entry);
  found.sort((a, b) => RANK(a) - RANK(b) || a.name.localeCompare(b.name));
  for (const fn of listeners) { try { fn(list()); } catch { /* a bad listener must not break discovery */ } }
}

/* best-effort name for a provider that did not identify itself through EIP-6963 */
function nameOf(p) {
  if (p.isPhantom) return "Phantom"; // Phantom also sets isMetaMask for compatibility, so test it first
  if (p.isCoinbaseWallet) return "Coinbase Wallet";
  if (p.isBraveWallet) return "Brave Wallet";
  if (p.isRabby) return "Rabby";
  if (p.isMetaMask) return "MetaMask";
  return "Browser wallet";
}

function readGlobals() {
  const cands = [];
  if (window.phantom && window.phantom.ethereum) cands.push(window.phantom.ethereum);
  const eth = window.ethereum;
  if (eth) for (const p of Array.isArray(eth.providers) && eth.providers.length ? eth.providers : [eth]) cands.push(p);
  for (const p of cands) {
    if (!p || typeof p.request !== "function") continue;
    const name = nameOf(p);
    add({ id: `legacy:${name.toLowerCase().replace(/\s+/g, "-")}`, name, icon: "", provider: p, source: "legacy" });
  }
}

export function startDiscovery() {
  if (started) return;
  started = true;
  window.addEventListener("eip6963:announceProvider", (ev) => {
    const d = ev && ev.detail;
    if (!d || !d.info || !d.provider || typeof d.provider.request !== "function") return;
    const name = String(d.info.name || "Browser wallet").slice(0, 40);
    // a legacy entry for the same provider is replaced by the better-described EIP-6963 one
    const i = found.findIndex((w) => w.provider === d.provider);
    if (i >= 0) found.splice(i, 1);
    add({ id: String(d.info.rdns || d.info.uuid || name), name, icon: ICON_OK.test(String(d.info.icon || "")) ? String(d.info.icon) : "", provider: d.provider, source: "eip6963" });
  });
  window.dispatchEvent(new Event("eip6963:requestProvider"));
  readGlobals();
  // some wallets inject a moment after load
  setTimeout(readGlobals, 400);
  setTimeout(readGlobals, 1500);
}

export const list = () => found.slice();
export function onWallets(fn) { listeners.add(fn); return () => listeners.delete(fn); }

/* Turn a wallet error into something a player can act on. EIP-1193 codes: 4001 rejected, -32002 request pending, 4902 unknown chain. */
export function explain(e) {
  const code = e && (e.code ?? (e.info && e.info.error && e.info.error.code));
  if (code === 4001 || code === "ACTION_REJECTED") return "You closed the wallet prompt. Nothing was sent.";
  if (code === -32002) return "Your wallet already has a request waiting. Open it and finish or cancel that first.";
  if (code === 4902) return "Your wallet does not know this network. Add it in the wallet first.";
  if (code === 4100) return "Your wallet is locked or has not approved this site. Unlock it and try again.";
  return String((e && (e.shortMessage || e.message)) || e).slice(0, 200);
}
