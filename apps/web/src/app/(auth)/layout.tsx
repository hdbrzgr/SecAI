import Link from "next/link";
import { Wordmark } from "@secai/ui";

export default function AuthLayout({ children }: LayoutProps<"/">) {
  return (
    <main className="flex flex-1 flex-col items-center px-4 py-12 sm:py-16">
      <Link href="/" aria-label="SecAI home" className="mb-8 inline-flex">
        <Wordmark size={32} />
      </Link>
      <div className="w-full max-w-[400px]">{children}</div>
    </main>
  );
}
