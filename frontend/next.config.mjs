/** @type {import('next').NextConfig} */

// Em producao o Nginx faz o proxy de /api; em dev o rewrite abaixo mantem tudo
// same-origin para que os cookies HttpOnly + CSRF funcionem sem CORS.
const apiUrl = process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000";

const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  // standalone somente na imagem Docker; localmente "next start" e usado nos testes.
  output: process.env.NEXT_OUTPUT === "standalone" ? "standalone" : undefined,
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${apiUrl}/:path*` }];
  },
};

export default nextConfig;
