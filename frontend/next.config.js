/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Make the API base URL available to client components.
  env: {
    NEXT_PUBLIC_API_URL:
      process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1",
  },
};

module.exports = nextConfig;
