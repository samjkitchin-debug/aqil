export function GET() {
  return new Response(null, { status: 404, headers: { "cache-control": "private, no-store" } });
}
