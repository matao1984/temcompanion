async function showLatestRelease() {
  const version = document.getElementById("latest-release-version");
  if (!version) return;

  try {
    const response = await fetch(
      "https://api.github.com/repos/matao1984/temcompanion/releases/latest"
    );
    if (!response.ok) {
      throw new Error(`GitHub returned HTTP ${response.status}`);
    }
    const release = await response.json();
    if (typeof release.tag_name !== "string" || !release.tag_name.trim()) {
      throw new Error("GitHub returned a release without a tag");
    }
    const published = new Date(release.published_at);
    if (typeof release.published_at !== "string" || Number.isNaN(published.getTime())) {
      console.error("GitHub returned a release without a valid publication date");
      version.textContent = `${release.tag_name} (release date unavailable)`;
      return;
    }
    const date = new Intl.DateTimeFormat("en", {
      year: "numeric",
      month: "long",
      day: "numeric",
      timeZone: "UTC",
    }).format(published);
    version.textContent = `${release.tag_name} (released ${date})`;
  } catch (error) {
    console.error("Could not retrieve the latest release:", error);
    version.textContent = "Unavailable; check the release link";
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", showLatestRelease);
} else {
  showLatestRelease();
}
