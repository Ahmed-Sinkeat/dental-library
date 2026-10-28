// Serves /media/<path under library/> from the private R2 bucket, with Range support for audio/video seeking.
// Everything else (index.html, catalog.json) is served by the assets binding.
const TYPES = {
  opus: "audio/ogg; codecs=opus", ogg: "audio/ogg", mp3: "audio/mpeg", aac: "audio/aac", m4a: "audio/mp4",
  "3gpp": "audio/3gpp", mp4: "video/mp4", pdf: "application/pdf", jpg: "image/jpeg", png: "image/png",
  rtf: "application/rtf", zip: "application/zip", doc: "application/msword", ppt: "application/vnd.ms-powerpoint",
  docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  pptx: "application/vnd.openxmlformats-officedocument.presentationml.presentation",
  pptm: "application/vnd.ms-powerpoint.presentation.macroEnabled.12",
};

export default {
  async fetch(request, env) {
    if (request.method !== "GET" && request.method !== "HEAD") return new Response("Method not allowed", { status: 405 });
    const path = decodeURIComponent(new URL(request.url).pathname.slice("/media/".length));
    if (!path || path.split("/").some((s) => s === ".." || s === ".") || path.startsWith("_")) return new Response("Not found", { status: 404 });

    const obj = await env.BUCKET.get(`library/${path}`, { range: request.headers });
    if (!obj) return new Response("Not found", { status: 404 });

    const h = new Headers();
    h.set("etag", obj.httpEtag);
    h.set("accept-ranges", "bytes");
    h.set("cache-control", "public, max-age=86400");
    const ext = path.split(".").pop().toLowerCase();
    h.set("content-type", TYPES[ext] || "application/octet-stream");
    if (!["pdf", "opus", "ogg", "mp3", "aac", "m4a", "mp4", "jpg", "png"].includes(ext)) {
      h.set("content-disposition", `attachment; filename*=UTF-8''${encodeURIComponent(path.split("/").pop())}`);
    }

    let status = 200, length = obj.size;
    if (obj.range && request.headers.has("range")) {
      const r = obj.range;
      const offset = r.suffix !== undefined ? obj.size - r.suffix : (r.offset ?? 0);
      length = r.suffix !== undefined ? r.suffix : (r.length ?? obj.size - offset);
      h.set("content-range", `bytes ${offset}-${offset + length - 1}/${obj.size}`);
      status = 206;
    }
    h.set("content-length", String(length));
    return new Response(request.method === "HEAD" ? null : obj.body, { status, headers: h });
  },
};
