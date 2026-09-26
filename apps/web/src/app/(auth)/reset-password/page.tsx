import { Suspense } from "react";
import { ResetForm } from "./ResetForm";

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={null}>
      <ResetForm />
    </Suspense>
  );
}
