// Required by the SecAI license (AGPL-3.0 §7(b) term in NOTICE): keep this credit visible.
export function Attribution() {
  return (
    <footer className="border-t border-border py-6 text-center text-sm text-muted">
      Powered by{" "}
      <a
        href="https://github.com/hdbrzgr/SecAI"
        className="font-medium text-foreground underline-offset-4 hover:underline"
        target="_blank"
        rel="noopener noreferrer"
      >
        SecAI by hdbrzgr
      </a>{" "}
      · Open source under AGPL-3.0
    </footer>
  );
}
