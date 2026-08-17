const http = require("http");
const fs = require("fs");
const path = require("path");

const listenHost = process.env.LM_STUDIO_PROXY_HOST || "127.0.0.1";
const listenPort = Number(process.env.LM_STUDIO_PROXY_PORT || 1235);
const targetHost = process.env.LM_STUDIO_TARGET_HOST || "127.0.0.1";
const targetPort = Number(process.env.LM_STUDIO_TARGET_PORT || 1234);
const logPath =
  process.env.LM_STUDIO_PROXY_LOG ||
  path.join(process.cwd(), "tmp", "lmstudio-request.log");

fs.mkdirSync(path.dirname(logPath), { recursive: true });

function appendLog(entry) {
  fs.appendFileSync(logPath, `${JSON.stringify(entry)}\n`, "utf8");
}

const server = http.createServer((clientRequest, clientResponse) => {
  const startedAt = Date.now();
  const entry = {
    at: new Date(startedAt).toISOString(),
    method: clientRequest.method,
    url: clientRequest.url,
    requestId: `${startedAt}-${Math.random().toString(16).slice(2)}`,
  };

  appendLog({ ...entry, event: "start" });

  const upstreamRequest = http.request(
    {
      host: targetHost,
      port: targetPort,
      method: clientRequest.method,
      path: clientRequest.url,
      headers: clientRequest.headers,
    },
    (upstreamResponse) => {
      clientResponse.writeHead(
        upstreamResponse.statusCode || 502,
        upstreamResponse.headers,
      );
      upstreamResponse.pipe(clientResponse);
      upstreamResponse.on("end", () => {
        appendLog({
          ...entry,
          event: "end",
          statusCode: upstreamResponse.statusCode,
          durationMs: Date.now() - startedAt,
        });
      });
    },
  );

  upstreamRequest.on("error", (error) => {
    appendLog({
      ...entry,
      event: "error",
      error: error.message,
      durationMs: Date.now() - startedAt,
    });
    if (!clientResponse.headersSent) {
      clientResponse.writeHead(502, { "content-type": "application/json" });
    }
    clientResponse.end(JSON.stringify({ error: error.message }));
  });

  clientRequest.pipe(upstreamRequest);
});

server.listen(listenPort, listenHost, () => {
  appendLog({
    at: new Date().toISOString(),
    event: "listen",
    listen: `${listenHost}:${listenPort}`,
    target: `${targetHost}:${targetPort}`,
  });
});
