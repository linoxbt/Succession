/**
 * Virtuals ACP — the earnings record a buyer can check without the seller.
 *
 * Every figure on this screen resolves to an on-chain job id. That is the whole
 * reason it sits apart from the data room's own counts, which are computed from
 * the seller's memory and therefore self-reported.
 */
import type { Preview } from "../api";
import { Badge, Empty, Field, FieldList, Section } from "../ui";

export function Agents({ preview }: { preview: Preview | null }) {
  const acp = preview?.acp;

  if (!acp) {
    return (
      <Section title="Virtuals ACP">
        <Empty>
          No ACP job history on this agent. Register it through the ACP Tech
          Playbook, then run <code className="font-mono">succession-acp sync</code>.
        </Empty>
      </Section>
    );
  }

  return (
    <div className="space-y-10">
      <Section title="Job history">
        <FieldList className="mt-4">
          <Field label="Completed jobs">
            <span className="tnum">{acp.completed_jobs}</span>
          </Field>
          <Field label="Failed or expired">
            <span className="tnum">{acp.failed_jobs}</span>
          </Field>
          <Field label="Gross volume">
            <span className="tnum">{acp.gross_volume}</span> USDC
          </Field>
          <Field label="Success rate">
            <span className="tnum">
              {acp.success_rate ? `${(Number(acp.success_rate) * 100).toFixed(0)}%` : "—"}
            </span>
            <span className="text-muted">
              {acp.success_rate ? " — feeds the valuation" : " — sample too small to score"}
            </span>
          </Field>
        </FieldList>
      </Section>

      <Section title="Registration">
        <FieldList className="mt-4">
          <Field label="Status">
            <Badge tone={acp.registered ? "closed" : "void"}>
              {acp.registered ? "On the service registry" : "Not registered"}
            </Badge>
          </Field>
          <Field label="Agent">{acp.agent_name || "—"}</Field>
          <Field label="Entity id">
            <span className="font-mono">{acp.agent_id ?? "—"}</span>
          </Field>
          <Field label="Wallet">
            <span className="font-mono break-all">{acp.agent_address || "—"}</span>
          </Field>
          <Field label="Counterparties">
            <span className="tnum">{acp.distinct_counterparties}</span>
          </Field>
          <Field label="Source">
            <Badge tone={acp.source === "live" ? "closed" : "neutral"}>{acp.source}</Badge>
          </Field>
        </FieldList>
      </Section>

      <Section
        title="Verifiable job ids"
        action={
          <span className="text-[0.8125rem] text-muted">Resolve against the ACP contract</span>
        }
      >
        <div className="mt-4 flex flex-wrap gap-1.5">
          {acp.verifiable_job_ids.map((id) => (
            <span
              key={id}
              className="border border-hairline px-2 py-0.5 font-mono text-[0.75rem] tnum text-muted"
            >
              #{id}
            </span>
          ))}
        </div>
        <p className="mt-4 text-[0.8125rem] text-muted">{acp.verification}</p>
      </Section>
    </div>
  );
}
