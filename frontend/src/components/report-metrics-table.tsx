import { Card } from "@/components/ui/card";
import type { Report } from "@/lib/api/contracts";

type Props = {
  title: string;
  rows: Report["metrics"]["consensus"];
};

export function ReportMetricsTable({ title, rows }: Props) {
  return (
    <Card className="overflow-x-auto">
      <h3 className="mb-3 text-base font-semibold text-slate-900">{title}</h3>
      {rows.length === 0 ? (
        <p className="text-sm text-slate-600">No data yet.</p>
      ) : (
        <table className="w-full min-w-[720px] border-collapse text-left text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-slate-700">
              <th className="p-2 font-medium">Statement</th>
              <th className="p-2 font-medium">Participation</th>
              <th className="p-2 font-medium">Agreement ratio</th>
              <th className="p-2 font-medium">Agree</th>
              <th className="p-2 font-medium">Disagree</th>
              <th className="p-2 font-medium">Pass</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id} className="border-b border-slate-100 align-top">
                <td className="p-2 text-slate-900">{row.text}</td>
                <td className="p-2">{row.participation}</td>
                <td className="p-2">{row.agreement_ratio.toFixed(2)}</td>
                <td className="p-2">{row.agree_count}</td>
                <td className="p-2">{row.disagree_count}</td>
                <td className="p-2">{row.pass_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}
