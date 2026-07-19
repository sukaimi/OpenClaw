export default function Footer() {
  return (
    <footer className="border-t border-border">
      <div className="mx-auto flex max-w-[1080px] flex-col items-center justify-between gap-2 px-5 py-8 text-[13px] text-body sm:flex-row">
        <p>
          SPARK v1 — SharePoint Autonomous Rebuild Kit
        </p>
        <p className="[font-feature-settings:'tnum']">
          &copy; {new Date().getFullYear()} Code &amp; Craft
        </p>
      </div>
    </footer>
  );
}
