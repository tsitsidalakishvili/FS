"use client";

import { useParams } from "next/navigation";

import { ReportMetricsTable } from "@/components/report-metrics-table";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import {
  useConversationQuery,
  useReportQuery,
  useRunAnalysisMutation,
} from "@/lib/api/hooks";

export default function ReportsPage() {
  const params = useParams<{ conversationId: string }>();
  const conversationId = params.conversationId;
  const conversationQuery = useConversationQuery(conversationId);
  const reportQuery = useReportQuery(conversationId);
  const runAnalysis = useRunAnalysisMutation(conversationId);

  if (conversationQuery.isLoading || reportQuery.isLoading) {
    return <LoadingState label="Loading report..." />;
  }
  if (conversationQuery.isError) {
    return (
      <ErrorState
        title="Could not load conversation"
        detail={conversationQuery.error.message}
      />
    );
  }
  if (reportQuery.isError) {
    return (
      <ErrorState
        title="Could not load report"
        detail={reportQuery.error.message}
      />
    );
  }

  const conversation = conversationQuery.data;
  const report = reportQuery.data;
  if (!conversation || !report) {
    return (
      <EmptyState
        title="No report data"
        detail="Participate and vote first, then run analysis."
      />
    );
  }

  return (
    <section className="space-y-4">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-slate-900">Monitor / Reports</h2>
          <p className="text-sm text-slate-600">
            Consensus, polarizing topics, and participant clustering.
          </p>
        </div>
        <Button
          type="button"
          disabled={runAnalysis.isPending}
          onClick={() => runAnalysis.mutate()}
        >
          {runAnalysis.isPending ? "Running analysis..." : "Run analysis"}
        </Button>
      </header>

      <div className="grid gap-3 sm:grid-cols-3">
        <Card>
          <p className="text-sm text-slate-600">Comments</p>
          <p className="text-2xl font-semibold">{report.metrics.total_comments}</p>
        </Card>
        <Card>
          <p className="text-sm text-slate-600">Participants</p>
          <p className="text-2xl font-semibold">{report.metrics.total_participants}</p>
        </Card>
        <Card>
          <p className="text-sm text-slate-600">Votes</p>
          <p className="text-2xl font-semibold">{report.metrics.total_votes}</p>
        </Card>
      </div>

      {runAnalysis.isError ? (
        <ErrorState title="Analysis failed" detail={runAnalysis.error.message} />
      ) : null}

      <Card>
        <h3 className="text-lg font-semibold text-slate-900">Potential agreements</h3>
        {report.potential_agreements.length === 0 ? (
          <p className="mt-2 text-sm text-slate-600">No strong agreement topics yet.</p>
        ) : (
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
            {report.potential_agreements.map((topic) => (
              <li key={topic}>{topic}</li>
            ))}
          </ul>
        )}
      </Card>

      <ReportMetricsTable title="Consensus statements" rows={report.metrics.consensus} />
      <ReportMetricsTable title="Polarizing statements" rows={report.metrics.polarizing} />

      <Card className="overflow-x-auto">
        <h3 className="mb-3 text-base font-semibold text-slate-900">Cluster summaries</h3>
        {report.cluster_summaries.length === 0 ? (
          <p className="text-sm text-slate-600">No cluster summaries available yet.</p>
        ) : (
          <table className="w-full min-w-[640px] border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-slate-700">
                <th className="p-2">Cluster</th>
                <th className="p-2">Size</th>
                <th className="p-2">Top agree</th>
                <th className="p-2">Top disagree</th>
              </tr>
            </thead>
            <tbody>
              {report.cluster_summaries.map((summary) => (
                <tr key={summary.cluster_id} className="border-b border-slate-100 align-top">
                  <td className="p-2">{summary.cluster_id}</td>
                  <td className="p-2">{summary.size}</td>
                  <td className="p-2">{summary.top_agree.join(", ") || "-"}</td>
                  <td className="p-2">{summary.top_disagree.join(", ") || "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <Card className="overflow-x-auto">
        <h3 className="mb-3 text-base font-semibold text-slate-900">Cluster similarity</h3>
        {report.cluster_similarity.length === 0 ? (
          <p className="text-sm text-slate-600">No similarity data available yet.</p>
        ) : (
          <table className="w-full min-w-[420px] border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-slate-700">
                <th className="p-2">Cluster A</th>
                <th className="p-2">Cluster B</th>
                <th className="p-2">Similarity</th>
              </tr>
            </thead>
            <tbody>
              {report.cluster_similarity.map((row) => (
                <tr
                  key={`${row.cluster_a}-${row.cluster_b}`}
                  className="border-b border-slate-100"
                >
                  <td className="p-2">{row.cluster_a}</td>
                  <td className="p-2">{row.cluster_b}</td>
                  <td className="p-2">{row.similarity.toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {!conversation.allow_viz ? (
        <Card>
          <p className="text-sm text-slate-600">
            Visualization is disabled in conversation settings (`allow_viz=false`).
          </p>
        </Card>
      ) : (
        <Card>
          <h3 className="text-base font-semibold text-slate-900">Cluster points</h3>
          <p className="mt-1 text-sm text-slate-600">
            {report.points.length} participant points available for plotting.
          </p>
        </Card>
      )}
    </section>
  );
}
