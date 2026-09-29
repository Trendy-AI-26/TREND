import Link from 'next/link'

export default function StudioPage() {
  return (
    <div className="mx-auto flex min-h-[50vh] max-w-3xl items-center justify-center px-4 py-12">
      <div className="w-full rounded-2xl border border-brand-accent/30 bg-white p-8 text-center shadow-sm">
        <p className="text-sm font-semibold uppercase tracking-wide text-brand-primary">
          Design Studio
        </p>
        <h1 className="mt-3 text-3xl font-semibold text-brand-headline">
          The studio is being prepared
        </h1>
        <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-muted-foreground">
          This workspace is reserved for the upcoming design tools. Your brand identity and generation flows remain available from the sidebar.
        </p>
        <Link
          href=".."
          className="mt-6 inline-flex h-10 items-center rounded-lg bg-brand-primary px-5 text-sm font-semibold text-white no-underline transition-opacity hover:opacity-90"
        >
          Back to generation
        </Link>
      </div>
    </div>
  )
}
