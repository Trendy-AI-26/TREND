
import createNextIntlPlugin from 'next-intl/plugin';

const withNextIntl = createNextIntlPlugin('./i18n/request.ts');
// Public base URL of the MinIO/S3 bucket host (e.g. https://s3.example.com).
// The backend returns image URLs like `{base}/{bucket}/{path}`.
const storageUrl = process.env.NEXT_PUBLIC_STORAGE_PUBLIC_URL;
const backendUrl = process.env.NEXT_SERVER_API_URL || 'http://127.0.0.1:8000';
const remotePatterns = [];

if (storageUrl) {
  const { protocol, hostname, port, pathname } = new URL(storageUrl);
  const basePath = pathname.replace(/\/+$/, '');

  remotePatterns.push({
    protocol: protocol.replace(':', ''),
    hostname,
    port,
    pathname: `${basePath}/**`,
  });
}

if (process.env.NODE_ENV === 'development') {
  remotePatterns.push({
    protocol: 'http',
    hostname: '127.0.0.1',
    port: '9000',
    pathname: '/brand-assets/**',
  });
}

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  images: {
    remotePatterns,
  },
  async rewrites() {
    return {
      beforeFiles: [],
      afterFiles: [],
      fallback: [
        {
          // Build-time destination. Set NEXT_SERVER_API_URL to the Render URL
          // in Vercel; local Docker keeps the localhost fallback.
          source: '/api/:path*',
          destination: `${backendUrl}/:path*`,
        },
      ],
    };
  },
};

export default withNextIntl(nextConfig);
