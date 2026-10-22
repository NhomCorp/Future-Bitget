"use strict";

const fs = require("fs");
const http = require("http");
const path = require("path");

const HOST = "127.0.0.1";
const PORT = 3007;
const ROOT = path.resolve(__dirname);

const TYPES = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".ico": "image/x-icon",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
};

function send(res, status, body, headers) {
  res.writeHead(status, { "Cache-Control": "no-store", ...headers });
  res.end(body);
}

const server = http.createServer((req, res) => {
  let pathname;
  try {
    pathname = decodeURIComponent(new URL(req.url || "/", `http://${HOST}:${PORT}`).pathname);
  } catch {
    send(res, 400, "Bad request");
    return;
  }

  if (pathname === "/") {
    pathname = "/index.html";
  }

  const filePath = path.normalize(path.join(ROOT, pathname));
  if (!filePath.startsWith(`${ROOT}${path.sep}`) && filePath !== ROOT) {
    send(res, 403, "Forbidden");
    return;
  }

  fs.stat(filePath, (err, stat) => {
    if (err || !stat.isFile()) {
      send(res, 404, "Not found");
      return;
    }

    const type = TYPES[path.extname(filePath).toLowerCase()] || "application/octet-stream";
    res.writeHead(200, {
      "Content-Type": type,
      "Cache-Control": "no-store",
    });
    fs.createReadStream(filePath).pipe(res);
  });
});

server.on("error", (err) => {
  if (err.code === "EADDRINUSE") {
    console.error(`Cổng ${PORT} đang bị chiếm. Đóng process cũ rồi chạy lại npm start.`);
    process.exit(1);
  }
  throw err;
});

server.listen(PORT, HOST, () => {
  console.log(`Frontend local: http://localhost:${PORT}`);
});
