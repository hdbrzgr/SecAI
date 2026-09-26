import { Suspense } from "react";
import { VerifyEmail } from "./VerifyEmail";

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={null}>
      <VerifyEmail />
    </Suspense>
  );
}
