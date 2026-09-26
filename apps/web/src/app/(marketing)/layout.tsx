import Link from "next/link";
import { Wordmark } from "@secai/ui";
import { ButtonLink } from "@/components/ButtonLink";

export default function MarketingLayout({ children }: LayoutProps<"/">) {
  return (
    <>
      <header className="sx-header">
        <div className="sx-header-inner justify-between">
          <Link href="/" aria-label="SecAI home" className="inline-flex">
            <Wordmark />
          </Link>
          <div className="flex gap-2">
            <ButtonLink href="/login" variant="ghost">
              Sign in
            </ButtonLink>
            <ButtonLink href="/register" variant="primary">
              Create account
            </ButtonLink>
          </div>
        </div>
      </header>
      <main className="flex-1">{children}</main>
    </>
  );
}
