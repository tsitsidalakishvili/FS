type PlaceholderPageProps = {
  title: string
}

export function PlaceholderPage(props: PlaceholderPageProps) {
  return (
    <section className="public-section">
      <h2>{props.title}</h2>
      <p>
        This legacy deep-link path is preserved. Its full feature set will be migrated in a later
        wave.
      </p>
    </section>
  )
}

