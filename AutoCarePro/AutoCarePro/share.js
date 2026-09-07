#!/usr/bin/env node
/* ==========================================================================
   AutoCare Pro — public link (Cloudflare quick tunnel)
   ==========================================================================

   Runs the app on this machine and exposes it on a public https link so any
   phone or PC, anywhere, can open it at the same time. The code never leaves
   this computer — the tunnel only forwards traffic to the local server.

       node share.js [port]

   Normally you don't call this directly: Run-AutoCare-Pro.bat offers it as
   option [2].

   What it does
   ------------
   1. starts the same static server as server.js
   2. finds cloudflared — on PATH, next to this file, or downloads it once
      (~40 MB, no account, no signup)
   3. spawns a quick tunnel, reads the generated URL out of its output
   4. prints one clear banner with every address, and cleans up on Ctrl+C

   Honest limits: the link lives only while this window is open, and a quick
   tunnel gets a new random URL each time. For a permanent link (Netlify,
   GitHub Pages) see docs/deploy.md.
   ========================================================================== */

const fs = require("fs");
const os = require("os");
const path = require("path");
const https = require("https");
const { spawn, execFile } = require("child_process");

const { start, openBrowser } = require("./server.js");

const ROOT = __dirname;
const PORT = Number(process.argv[2]) || 5500;

const BIN = {
  win32: { file: "cloudflared.exe", asset: "cloudflared-windows-amd64.exe" },
  darwin: { file: "cloudflared", asset: "cloudflared-darwin-amd64.tgz" },
  linux: { file: "cloudflared", asset: "cloudflared-linux-amd64" },
};

const RELEASE = "https://github.com/cloudflare/cloudflared/releases/latest/download";
const URL_RE = /https:\/\/[a-z0-9-]+\.trycloudflare\.com/i;

/* ------------------------------------------------------------- locating -- */

/** Is `cloudflared` already installed and on PATH? */
function onPath() {
  return new Promise((resolve) => {
    execFile(process.platform === "win32" ? "where" : "which", ["cloudflared"], (err, stdout) => {
      resolve(err ? null : String(stdout).split(/\r?\n/)[0].trim() || null);
    });
  });
}

function download(url, dest, redirects = 0) {
  return new Promise((resolve, reject) => {
    if (redirects > 5) return reject(new Error("Too many redirects."));

    const req = https
      .get(url, { headers: { "User-Agent": "AutoCarePro" }, timeout: 20000 }, (res) => {
        // GitHub release assets answer with a redirect to a CDN.
        if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
          res.resume();
          return resolve(download(res.headers.location, dest, redirects + 1));
        }
        if (res.statusCode !== 200) {
          res.resume();
          return reject(new Error(`Download failed (HTTP ${res.statusCode}).`));
        }

        const total = Number(res.headers["content-length"]) || 0;
        let done = 0;
        let lastPct = -1;

        // Write to a .part file and rename only on success, so an interrupted
        // download can never leave a truncated binary that looks installed.
        const partial = `${dest}.part`;
        const file = fs.createWriteStream(partial);
        res.on("data", (chunk) => {
          done += chunk.length;
          if (total) {
            const pct = Math.floor((done / total) * 100);
            if (pct !== lastPct && pct % 5 === 0) {
              lastPct = pct;
              process.stdout.write(`\r   Downloading cloudflared... ${pct}%   `);
            }
          }
        });
        res.pipe(file);

        const fail = (err) => {
          file.destroy();
          fs.unlink(partial, () => reject(err));
        };

        res.on("error", fail);
        file.on("error", fail);

        file.on("finish", () =>
          file.close(() => {
            // A few kilobytes means we saved an error page, not a binary.
            if (fs.statSync(partial).size < 1_000_000) {
              return fail(new Error("Download was incomplete."));
            }
            fs.renameSync(partial, dest);
            process.stdout.write("\r   Downloading cloudflared... done.        \n");
            resolve(dest);
          })
        );
      })
      .on("error", reject);

    // Without this a blocked or silent network would hang the launcher forever.
    req.on("timeout", () => {
      req.destroy(new Error("Download timed out — the network did not respond."));
    });
  });
}

async function ensureCloudflared() {
  const spec = BIN[process.platform];
  if (!spec) throw new Error(`Unsupported platform: ${process.platform}`);

  const local = path.join(ROOT, spec.file);
  if (fs.existsSync(local)) return local;

  const found = await onPath();
  if (found) return "cloudflared";

  if (process.platform === "darwin") {
    throw new Error(
      "cloudflared is not installed. Install it with:  brew install cloudflared"
    );
  }

  console.log("   cloudflared not found — downloading it once (~40 MB).");
  console.log("   No account and no signup required.\n");
  await download(`${RELEASE}/${spec.asset}`, local);
  if (process.platform !== "win32") fs.chmodSync(local, 0o755);
  return local;
}

/* --------------------------------------------------------------- output -- */

function banner({ url, lan, port, publicUrl }) {
  const line = "   " + "=".repeat(62);
  console.log("");
  console.log(line);
  console.log("      A U T O C A R E   P R O   —   L I V E");
  console.log(line);
  console.log("");
  if (publicUrl) {
    console.log("   PUBLIC LINK  (share this with anyone, any device)");
    console.log("");
    console.log(`        ${publicUrl}`);
    console.log("");
  }
  console.log(`   This computer   ${url}`);
  if (lan) console.log(`   Same Wi-Fi      http://${lan}:${port}/index.html`);
  console.log("");
  console.log("   Keep this window open. Closing it kills the link.");
  console.log("   Stop everything   Ctrl + C");
  console.log(line);
  console.log("");
}

/* ----------------------------------------------------------------- main -- */

async function main() {
  const { port, url, lan } = await start(PORT);
  console.log(`\n   Local server running on port ${port}.`);

  let bin;
  try {
    bin = await ensureCloudflared();
  } catch (err) {
    console.log("");
    console.log("   Could not set up the tunnel: " + err.message);
    console.log("");
    console.log("   The app is still running locally — see the addresses below.");
    console.log("   For a permanent public link without any download, drag this");
    console.log("   folder onto https://app.netlify.com/drop  (see docs/deploy.md).");
    banner({ url, lan, port, publicUrl: null });
    openBrowser(url);
    return;
  }

  console.log("   Opening the tunnel...\n");

  const child = spawn(bin, ["tunnel", "--url", `http://localhost:${port}`], {
    stdio: ["ignore", "pipe", "pipe"],
  });

  let announced = false;
  const scan = (buf) => {
    const text = String(buf);
    const match = text.match(URL_RE);
    if (match && !announced) {
      announced = true;
      banner({ url, lan, port, publicUrl: match[0] });
      openBrowser(url);
    }
  };
  child.stdout.on("data", scan);
  child.stderr.on("data", scan); // cloudflared prints the URL on stderr

  const timer = setTimeout(() => {
    if (!announced) {
      console.log("   Still waiting for the tunnel URL...");
      console.log("   If nothing appears, check your internet connection, or use");
      console.log("   the permanent hosting route in docs/deploy.md.\n");
    }
  }, 25000);

  const shutdown = () => {
    clearTimeout(timer);
    if (!child.killed) child.kill();
    console.log("\n   Tunnel closed. The public link no longer works.\n");
    process.exit(0);
  };

  process.on("SIGINT", shutdown);
  process.on("SIGTERM", shutdown);
  child.on("exit", (code) => {
    clearTimeout(timer);
    if (code !== 0 && !announced) {
      console.log(`\n   The tunnel could not be established (cloudflared exit ${code}).`);
      console.log("   Usually this means no internet, or a firewall/college network");
      console.log("   blocking outbound tunnels. The app itself is fine — it is");
      console.log("   still running locally at the addresses below.");
      console.log("");
      console.log("   For a public link that needs no tunnel at all, drag this");
      console.log("   folder onto https://app.netlify.com/drop (see docs/deploy.md).");
      banner({ url, lan, port, publicUrl: null });
      openBrowser(url);
    }
  });
}

main().catch((err) => {
  console.error("\n   Failed to start:", err.message, "\n");
  process.exit(1);
});
