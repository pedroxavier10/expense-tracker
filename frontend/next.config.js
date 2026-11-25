/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Make the API base URL available to client components.
  env: {
    NEXT_PUBLIC_API_URL:
      process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1",
  },
  async headers() {
    return [
      {
        // The browser must always revalidate the worker script, otherwise
        // new deployments could take up to 24h to reach installed apps.
        source: "/sw.js",
        headers: [
          { key: "Cache-Control", value: "no-cache, no-store, must-revalidate" },
          { key: "Service-Worker-Allowed", value: "/" },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
