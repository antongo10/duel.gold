/* Connecting browser wallets, in real Chromium against the dev stack.

   MetaMask and Phantom cannot be installed in a headless sandbox, so the page is given two faithful mocks of the same
   protocol the real extensions speak: EIP-1193 (`request`, `on`) and EIP-6963 (announce). One mock announces itself
   like MetaMask; the other exists only as `window.phantom.ethereum` and, like the real Phantom, also claims
   `isMetaMask`. Signatures and on-chain deposits are REAL: the mocks forward personal_sign and eth_sendTransaction to
   ethers wallets in Node, so the server verifies genuine signatures and deposits are genuine transactions.
   What this does not prove: behaviour of the actual extensions' UIs (see README). */
import test, { before, after } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright-core";
import { Wallet, parseEther, verifyMessage } from "ethers";
import { startDevStack } from "../scripts/dev-stack.js";

const here = path.dirname(fileURLToPath(import.meta.url));
const SHOTS = path.join(here, "shots");
const CHROME = ["/opt/pw-browsers/chromium-1194/chrome-linux/chrome", "/opt/pw-browsers/chromium/chrome-linux/chrome", process.env.CHROME_PATH].find((p) => p && fs.existsSync(p));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const SKIP = !CHROME && "no Chromium available";

let stack, browser;
before(async () => {
  if (!CHROME) return;
  fs.mkdirSync(SHOTS, { recursive: true });
  stack = await startDevStack({ memory: true, quiet: true, overrides: { rate: { authPerMin: 1000, apiPerMin: 100000, wsPerSec: 200 } } });
  browser = await chromium.launch({ executablePath: CHROME, args: ["--no-sandbox"] });
});
after(async () => {
  if (browser) await browser.close();
  if (stack) await stack.stop();
});

const until = async (fn, label, ms = 12000) => {
  const end = Date.now() + ms;
  for (;;) {
    try { const v = await fn(); if (v) return v; } catch { /* page navigating */ }
    if (Date.now() > end) throw new Error("timed out: " + label);
    await sleep(60);
  }
};
const text = (page, sel) => page.locator(sel).first().innerText();
const noOverflow = (page) => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth);
const calls = (page) => page.evaluate(() => window.__mock.calls);
const MM_ICON = "data:image/svg+xml;base64," + Buffer.from('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><rect width="24" height="24" rx="6" fill="#f6851b"/></svg>').toString("base64");

/* Open the page with two mock wallets installed. MetaMask is on the local chain, Phantom deliberately on Sepolia. */
async function openWithWallets(width = 1280) {
  const wallets = { MetaMask: Wallet.createRandom().connect(stack.provider), Phantom: Wallet.createRandom().connect(stack.provider) };
  for (const w of Object.values(wallets)) await (await stack.faucet.sendTransaction({ to: w.address, value: parseEther("1") })).wait();
  const ctx = await browser.newContext({ viewport: { width, height: 900 } });
  const page = await ctx.newPage();
  page.errors = [];
  page.on("pageerror", (e) => page.errors.push("pageerror: " + e.message));
  page.on("console", (m) => { if (m.type() === "error" && !/fonts\.g|ERR_FAILED|favicon/.test(m.text() + (m.location().url || ""))) page.errors.push("console: " + m.text()); });
  await page.route(/fonts\.(googleapis|gstatic)\.com/, (r) => r.abort());
  await page.exposeFunction("__walletSign", (name, message) => wallets[name].signMessage(message));
  await page.exposeFunction("__walletSend", async (name, tx) => (await wallets[name].sendTransaction({ to: tx.to, value: BigInt(tx.value) })).hash);
  await page.addInitScript(({ accounts, chains, icon }) => {
    const state = (window.__mock = { calls: [], rejectNext: false });
    const make = (name, flags) => {
      const listeners = {};
      const p = {
        ...flags, _chain: chains[name],
        async request({ method, params = [] }) {
          state.calls.push({ wallet: name, method, params });
          if (state.rejectNext && ["eth_requestAccounts", "personal_sign", "eth_sendTransaction"].includes(method)) {
            state.rejectNext = false;
            throw Object.assign(new Error("User rejected the request."), { code: 4001 });
          }
          switch (method) {
            case "eth_requestAccounts": case "eth_accounts": return [accounts[name].toLowerCase()];
            case "eth_chainId": return p._chain;
            case "personal_sign": { // ethers hex-encodes the UTF-8 message
              const bytes = new Uint8Array(params[0].slice(2).match(/../g).map((h) => parseInt(h, 16)));
              return window.__walletSign(name, new TextDecoder().decode(bytes));
            }
            case "eth_sendTransaction": return window.__walletSend(name, params[0]);
            case "wallet_switchEthereumChain": p._chain = params[0].chainId; (listeners.chainChanged || []).forEach((f) => f(p._chain)); return null;
            default: throw Object.assign(new Error("unsupported method " + method), { code: -32601 });
          }
        },
        on(ev, fn) { (listeners[ev] = listeners[ev] || []).push(fn); },
        removeListener(ev, fn) { listeners[ev] = (listeners[ev] || []).filter((f) => f !== fn); },
        _emit(ev, ...a) { (listeners[ev] || []).forEach((f) => f(...a)); },
        _count(ev) { return (listeners[ev] || []).length; },
      };
      return p;
    };
    const mm = make("MetaMask", { isMetaMask: true });
    const ph = make("Phantom", { isPhantom: true, isMetaMask: true }); // the real Phantom also sets isMetaMask
    state.providers = { MetaMask: mm, Phantom: ph };
    const announce = () => window.dispatchEvent(new CustomEvent("eip6963:announceProvider", { detail: Object.freeze({ info: { uuid: "0000-mm", name: "MetaMask", icon, rdns: "io.metamask" }, provider: mm }) }));
    window.addEventListener("eip6963:requestProvider", announce);
    announce();
    window.phantom = { ethereum: ph }; // Phantom: global only, no EIP-6963 here
    window.ethereum = mm; // the "default" wallet, as on a machine with both installed
  }, { accounts: { MetaMask: wallets.MetaMask.address, Phantom: wallets.Phantom.address }, chains: { MetaMask: "0x7a69", Phantom: "0xaa36a7" }, icon: MM_ICON });
  await page.goto(`${stack.url}/play/?test=1`);
  return { page, wallets };
}

test("the picker finds MetaMask (EIP-6963) and Phantom (global) without duplicates, and explains a missing wallet", { skip: SKIP }, async () => {
  const { page } = await openWithWallets();
  await page.waitForSelector("[data-test=wallet-metamask]");
  await page.waitForSelector("[data-test=wallet-phantom]");
  assert.equal(await page.locator("[data-act=wallet]").count(), 2, "window.ethereum is the same provider as the EIP-6963 MetaMask: listed once");
  assert.equal(await page.locator("[data-test=wallet-metamask] img").count(), 1, "the wallet's own icon is shown");
  assert.equal(await page.locator("[data-test=wallet-phantom] img").count(), 0);
  assert.equal(await page.locator("[data-act=wallet]").first().innerText(), "Connect MetaMask", "MetaMask is listed first");
  await page.screenshot({ path: path.join(SHOTS, "20-wallet-picker-1280.png"), fullPage: true });
  await page.setViewportSize({ width: 360, height: 780 });
  assert.ok(await noOverflow(page));
  await page.screenshot({ path: path.join(SHOTS, "21-wallet-picker-360.png"), fullPage: true });
  assert.deepEqual(page.errors, []);

  // a browser with no wallet gets install links and the burner option instead of a dead end
  const bare = await (await browser.newContext()).newPage();
  await bare.route(/fonts\.(googleapis|gstatic)\.com/, (r) => r.abort());
  await bare.goto(`${stack.url}/play/?test=1`);
  await bare.waitForSelector("#noWallet");
  assert.match(await text(bare, "#noWallet"), /MetaMask.*Phantom/s);
  assert.equal(await bare.locator("#noWallet a[target=_blank][rel~=noopener]").count(), 2);
  assert.ok(await bare.locator("#signBurner").isVisible());
});

test("connect Phantom: a real signature signs in, the wallet's chain is in the message, switch network, deposit from the wallet on-chain", { skip: SKIP }, async () => {
  const { page, wallets } = await openWithWallets();
  await page.click("[data-test=wallet-phantom]");
  await page.waitForSelector("#balAvail");
  const me = await page.evaluate(() => window.__duel.S.me);
  assert.equal(me.address, wallets.Phantom.address, "signed in as the wallet's own address");
  assert.match(await text(page, "#topRight"), /Phantom/, "the header names the wallet");

  // the message the wallet signed: server domain + the wallet's chain (Sepolia here), and it verifies for that address
  const sign = (await calls(page)).find((c) => c.method === "personal_sign");
  const message = Buffer.from(sign.params[0].slice(2), "hex").toString("utf8");
  assert.match(message, new RegExp(`^localhost:${new URL(stack.url).port} wants you to sign in with your Ethereum account:\\n${wallets.Phantom.address}\\n`));
  assert.match(message, /\nChain ID: 11155111\n/, "the wallet's current chain, so it shows no mismatch warning");
  assert.match(message, /\nURI: http:\/\/localhost:\d+\n/);
  assert.equal(sign.params[1].toLowerCase(), wallets.Phantom.address.toLowerCase(), "asked to sign with the connected account");
  assert.equal(verifyMessage(message, await wallets.Phantom.signMessage(message)), wallets.Phantom.address);
  assert.ok(!(await calls(page)).some((c) => c.method === "eth_sendTransaction"), "signing in sent no transaction");

  // wallet is on Sepolia, the server's chain is the local one: deposits are blocked until it switches
  await page.waitForSelector("#wrongChain");
  assert.match(await text(page, "#wrongChain"), /Sepolia.*Switch to Local/s);
  assert.equal(await page.locator("#depAmt").count(), 0, "no deposit button on the wrong network");
  await page.screenshot({ path: path.join(SHOTS, "22-lobby-wrong-chain-1280.png"), fullPage: true });
  await page.click("#switchBtn");
  await page.waitForSelector("#depAmt");
  const sw = (await calls(page)).find((c) => c.method === "wallet_switchEthereumChain");
  assert.deepEqual(sw.params, [{ chainId: "0x7a69" }]);

  // deposit 0.05 from the wallet: a real transaction to the player's own deposit address
  const depositAddress = await text(page, "#depositAddr");
  await page.fill("#depAmt", "0.05");
  await page.click("#depBtn");
  await until(async () => (await text(page, "#balAvail")) === "0.05", "deposit credited");
  const tx = (await calls(page)).find((c) => c.method === "eth_sendTransaction");
  assert.equal(tx.params[0].to.toLowerCase(), depositAddress.toLowerCase());
  assert.equal(BigInt(tx.params[0].value), parseEther("0.05"));
  assert.equal(tx.params[0].from.toLowerCase(), wallets.Phantom.address.toLowerCase());
  assert.equal(stack.app.ledger.audit().ok, true);

  // validation and cancellation are explained, not silent
  await page.fill("#depAmt", "0");
  await page.click("#depBtn");
  assert.match(await text(page, "#depErr"), /above zero/);
  await page.fill("#depAmt", "0.01");
  await page.evaluate(() => { window.__mock.rejectNext = true; });
  await page.click("#depBtn");
  await until(async () => /closed the wallet prompt/i.test(await text(page, "#depErr")), "rejection explained");
  assert.equal(await text(page, "#balAvail"), "0.05", "a cancelled deposit changes nothing");

  assert.deepEqual(page.errors, []);
});

test("changing account or disconnecting in the wallet signs the player out; a rejected connect is explained", { skip: SKIP }, async () => {
  const { page } = await openWithWallets();
  // the player closes the wallet prompt
  await page.evaluate(() => { window.__mock.rejectNext = true; });
  await page.click("[data-test=wallet-metamask]");
  await until(async () => /closed the wallet prompt/i.test(await text(page, "#err")), "rejection explained");
  assert.ok(await page.locator("[data-act=wallet]").first().isEnabled(), "the player can try again");

  await page.click("[data-test=wallet-metamask]");
  await page.waitForSelector("#balAvail");
  const token = await page.evaluate(() => window.__duel.client.token);
  assert.equal(await page.evaluate(() => window.__mock.providers.MetaMask._count("accountsChanged")), 1, "the page listens to the wallet");

  // another account selected in the wallet: the session is for the old one, so it ends
  await page.evaluate(() => window.__mock.providers.MetaMask._emit("accountsChanged", ["0x" + "22".repeat(20)]));
  await page.waitForSelector("[data-act=wallet]");
  assert.equal(await page.evaluate(() => window.__duel.S.view), "signin");
  assert.equal(await page.evaluate(() => window.__mock.providers.MetaMask._count("accountsChanged")), 0, "listeners are removed on sign-out");
  await until(async () => (await fetch(stack.url + "/v1/me", { headers: { authorization: `Bearer ${token}` } })).status === 401, "server session ended");

  // disconnect event
  await page.click("[data-test=wallet-metamask]");
  await page.waitForSelector("#balAvail");
  await page.evaluate(() => window.__mock.providers.MetaMask._emit("disconnect"));
  await page.waitForSelector("[data-act=wallet]");
});

test("after a reload the session resumes and the wallet re-attaches without another prompt", { skip: SKIP }, async () => {
  const { page, wallets } = await openWithWallets();
  await page.click("[data-test=wallet-metamask]");
  await page.waitForSelector("#depAmt"); // MetaMask mock is already on the local chain
  await page.reload();
  await page.waitForSelector("#balAvail");
  await until(() => page.locator("#depAmt").count().then((n) => n === 1), "wallet re-attached after reload");
  const after = await calls(page);
  assert.ok(after.some((c) => c.method === "eth_accounts"), "re-attached by asking for already-approved accounts");
  assert.ok(!after.some((c) => c.method === "eth_requestAccounts" || c.method === "personal_sign"), "no new prompt and no new signature");
  assert.equal(await page.evaluate(() => window.__duel.S.me.address), wallets.MetaMask.address);
});
