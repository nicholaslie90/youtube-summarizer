// Proxy to the Mac's local server. Cloudflare Access (workers.dev toggle) gates who reaches this.
export default {
  async fetch(req, env) {
    const { pathname, search } = new URL(req.url);
    try {
      return await env.APP.fetch(`http://127.0.0.1:8765${pathname}${search}`, req);
    } catch {
      return new Response("Mac is offline or the app isn't running.", { status: 503 });
    }
  },
};
