#!/usr/bin/env node
/* ==========================================================================
   AutoCare Pro — zero-dependency static server
   ==========================================================================

   Serves this folder over http:// so the PWA layer (service worker, install
   prompt, offline cache) can actually run — browsers refuse to register a
   service worker on file://.

   Standalone:
       node server.js [port]

   As a module (used by share.js):
       const { start } = require("./server.js");
       const { port, url, lan } = await start(5500);

   It binds every interface, so a phone on the same Wi-Fi can open the app,
   and it walks upward from the requested port until it finds a free one.
   No npm install, no dependencies.
   ========================================================================== */

const http = require("http");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { exec } = require("child_process");

const ROOT = __dirname;
const MAX_TRIES = 20;

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
  ".woff2": "font/woff2",
  ".md": "text/markdown; charset=utf-8",
  ".txt": "text/plain; charset=utf-8",
};

function createServer() {
  return http.createServer((req, res) => {
    let pathname;
    try {
      pathname = decodeURIComponent(new URL(req.url, "http://localhost").pathname);
    } catch (err) {
      res.writeHead(400).end("Bad request");
      return;
    }

    if (pathname === "/") pathname = "/index.html";

    const filePath = path.join(ROOT, pathname);

    // Never serve anything outside the project folder.
    if (!filePath.startsWith(ROOT)) {
      res.writeHead(403).end("Forbidden");
      return;
    }

    fs.stat(filePath, (err, stat) => {
      if (err || stat.isDirectory()) {
        res.writeHead(404, { "Content-Type": "text/html; charset=utf-8" });
        res.end("<h1>404</h1><p>Not found. <a href='/'>Back to AutoCare Pro</a></p>");
        return;
      }
      res.writeHead(200, {
        "Content-Type": MIME[path.extname(filePath).toLowerCase()] || "application/octet-stream",
        // The service worker must always be revalidated or updates never land.
        "Cache-Control": pathname.includes("service-worker") ? "no-cache" : "no-store",
      });
      fs.createReadStream(filePath).pipe(res);
    });
  });
}

/**
 * Start listening, walking upward from `startPort` past any busy ports.
 * @returns {Promise<{server, port:number, url:string, lan:string|null}>}
 */
function start(startPort = 5500) {
  return new Promise((resolve, reject) => {
    const server = createServer();

    const attempt = (port, tries) => {
      const onError = (err) => {
        if (err.code === "EADDRINUSE" && tries < MAX_TRIES) {
          attempt(port + 1, tries + 1);
        } else {
          reject(err);
        }
      };
      server.once("error", onError);
      server.listen(port, () => {
        server.removeListener("error", onError);
        resolve({
          server,
          port,
          url: `http://localhost:${port}/index.html`,
          lan: lanAddress(),
        });
      });
    };

    attempt(startPort, 0);
  });
}

/** First non-internal IPv4 address — the one other devices on the Wi-Fi reach. */
function lanAddress() {
  const nets = os.networkInterfaces();
  for (const name of Object.keys(nets)) {
    for (const net of nets[name] || []) {
      if (net.family === "IPv4" && !net.internal) return net.address;
    }
  }
  return null;
}

function openBrowser(url) {
  const cmd =
    process.platform === "win32"
      ? `start "" "${url}"`
      : process.platform === "darwin"
      ? `open "${url}"`
      : `xdg-open "${url}"`;
  exec(cmd, (err) => {
    if (err) console.log("   (Open the link above in your browser manually.)");
  });
}

module.exports = { createServer, start, lanAddress, openBrowser, ROOT };

/* ------------------------------------------------------------ standalone -- */

if (require.main === module) {
  start(Number(process.argv[2]) || 5500)
    .then(({ port, url, lan }) => {
      console.log("");
      console.log("   AUTOCARE PRO  //  Smart Vehicle Maintenance System");
      console.log("   ------------------------------------------------------");
      console.log(`   This computer   ${url}`);
      if (lan) {
        console.log(`   Same Wi-Fi      http://${lan}:${port}/index.html`);
        console.log("                   ^ open this on your phone or another PC");
      }
      console.log("   Stop server     Ctrl + C");
      console.log("");
      openBrowser(url);
    })
    .catch((err) => {
      console.error("\n  Could not start the server:", err.message, "\n");
      process.exit(1);
    });
}
