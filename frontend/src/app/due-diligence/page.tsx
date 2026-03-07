"use client";

import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";

const workflowSteps = [
  {
    id: "start",
    title: "1) Start Point",
    detail: "Investigation starts from CRM context or direct competitor lead.",
    when: "At intake",
  },
  {
    id: "resolve",
    title: "2) Entity Resolution",
    detail: "Map person/company to canonical graph identity.",
    when: "Before enrichment",
  },
  {
    id: "enrich",
    title: "3) Enrichment",
    detail: "Pull source-linked data (Wikidata, OpenSanctions, news).",
    when: "On analyst action",
  },
  {
    id: "weekly",
    title: "4) Weekly Monitoring",
    detail: "Scheduled refresh for media-linked graph edges.",
    when: "Weekly",
  },
  {
    id: "risk",
    title: "5) Risk View",
    detail: "Run network checks, including risky two-hop relationships.",
    when: "During analysis",
  },
  {
    id: "report",
    title: "6) Report & Actions",
    detail: "Generate evidence-backed report and CRM follow-up actions.",
    when: "At export",
  },
];

const appUrl =
  process.env.NEXT_PUBLIC_DUE_DILIGENCE_APP_URL?.trim().replace(/\/+$/, "") ?? "";

function buildLaunchUrl(baseUrl: string, params: Record<string, string>) {
  const url = new URL(baseUrl);
  Object.entries(params).forEach(([key, value]) => {
    if (value.trim()) {
      url.searchParams.set(key, value.trim());
    }
  });
  return url.toString();
}

export default function DueDiligencePage() {
  const [startMode, setStartMode] = useState("crm_context");
  const [subject, setSubject] = useState("");
  const [subjectType, setSubjectType] = useState("Person");

  const launchUrl = useMemo(() => {
    if (!appUrl) {
      return "";
    }
    return buildLaunchUrl(appUrl, {
      subject,
      subject_type: subjectType,
      start_mode: startMode,
    });
  }, [startMode, subject, subjectType]);

  return (
    <section className="space-y-4">
      <header>
        <h2 className="text-2xl font-semibold text-slate-900">Due Diligence</h2>
        <p className="text-sm text-slate-600">
          Preserved Streamlit journey: workflow architecture + external app launch.
        </p>
      </header>

      <Card>
        <h3 className="mb-3 text-lg font-semibold text-slate-900">How it works</h3>
        <ol className="grid gap-3">
          {workflowSteps.map((step) => (
            <li key={step.id} className="rounded-lg border border-slate-200 p-3">
              <p className="font-medium text-slate-900">{step.title}</p>
              <p className="mt-1 text-sm text-slate-600">{step.detail}</p>
              <p className="mt-1 text-xs text-slate-500">When: {step.when}</p>
            </li>
          ))}
        </ol>
      </Card>

      <Card className="space-y-3">
        <h3 className="text-lg font-semibold text-slate-900">Actual app launch</h3>
        <p className="text-sm text-slate-600">
          Prefill subject and mode, then open the dedicated due diligence app.
        </p>

        <label className="block text-sm">
          <span className="mb-1 block font-medium text-slate-800">Start mode</span>
          <Select value={startMode} onChange={(event) => setStartMode(event.target.value)}>
            <option value="crm_context">CRM context</option>
            <option value="competitor_person">Competitor person</option>
            <option value="competitor_company">Competitor company</option>
            <option value="competitor_watchlist">Competitor watchlist</option>
          </Select>
        </label>
        <label className="block text-sm">
          <span className="mb-1 block font-medium text-slate-800">Subject</span>
          <Input
            value={subject}
            onChange={(event) => setSubject(event.target.value)}
            placeholder="Person or company name"
          />
        </label>
        <label className="block text-sm">
          <span className="mb-1 block font-medium text-slate-800">Subject type</span>
          <Select value={subjectType} onChange={(event) => setSubjectType(event.target.value)}>
            <option value="Person">Person</option>
            <option value="Company">Company</option>
          </Select>
        </label>

        {appUrl ? (
          <div className="flex flex-wrap items-center gap-3">
            <a href={launchUrl || appUrl} target="_blank" rel="noreferrer">
              <Button type="button">Open DD app</Button>
            </a>
            <p className="break-all text-xs text-slate-500">{launchUrl || appUrl}</p>
          </div>
        ) : (
          <p className="text-sm text-amber-700">
            Set <code>NEXT_PUBLIC_DUE_DILIGENCE_APP_URL</code> to enable launch.
          </p>
        )}
      </Card>
    </section>
  );
}
