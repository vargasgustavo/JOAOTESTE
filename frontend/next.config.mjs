/** @type {import('next').NextConfig} */

// Em producao o Nginx faz o proxy de /api; em dev o rewrite abaixo mantem tudo
// same-origin para que os cookies HttpOnly + CSRF funcionem sem CORS.
const apiUrl = process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000";

const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  output: "standalone",
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${apiUrl}/:path*` }];
  },
};

export default nextConfig;
