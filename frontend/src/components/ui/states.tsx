import { Card } from "@/components/ui/card";

export function LoadingState({ label = "Loading..." }: { label?: string }) {
  return (
    <Card role="status" aria-live="polite" className="animate-pulse">
      <p className="text-sm text-slate-600">{label}</p>
    </Card>
  );
}

export function ErrorState({
  title = "Something went wrong",
  detail,
}: {
  title?: string;
  detail?: string;
}) {
  return (
    <Card className="border-red-200 bg-red-50">
      <h2 className="text-base font-semibold text-red-900">{title}</h2>
      {detail ? <p className="mt-1 text-sm text-red-700">{detail}</p> : null}
    </Card>
  );
}

export function EmptyState({
  title,
  detail,
}: {
  title: string;
  detail: string;
}) {
  return (
    <Card>
      <h2 className="text-base font-semibold text-slate-900">{title}</h2>
      <p className="mt-1 text-sm text-slate-600">{detail}</p>
    </Card>
  );
}
